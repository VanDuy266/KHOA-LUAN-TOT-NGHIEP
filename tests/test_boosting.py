"""Checks for the CatBoost/XGBoost experiment and native contribution outputs."""
from pathlib import Path
import sys,json,unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'app')]
from battery_soh.features import FEATURES

@unittest.skipUnless((ROOT/'reports/boosting/metadata.json').exists(),'Complete experiment first')
class BoostingChecks(unittest.TestCase):
    def test_same_rows_and_outer_folds(self):
        data=pd.read_csv(ROOT/'reports/features.csv')
        pred=pd.read_csv(ROOT/'reports/boosting/predictions.csv')
        folds=pd.read_csv(ROOT/'reports/split_assignments.csv').set_index('battery').test_fold
        for name in ['CatBoost','XGBoost']:
            part=pred[pred.model==name]
            self.assertEqual(len(part),len(data));self.assertEqual(part.battery.nunique(),86)
            self.assertFalse(part.duplicated(['battery','phase','cycle']).any())
            self.assertTrue((part.fold==part.battery.map(folds)).all())
            self.assertTrue(np.isfinite(part[['actual_soh','predicted_soh']]).all().all())
    def test_inner_selection_never_sees_test_devices(self):
        splits=json.loads((ROOT/'reports/boosting/splits.json').read_text())
        for split in splits:
            fit=set(split['fit_batteries']);validation=set(split['validation_batteries']);test=set(split['test_batteries'])
            self.assertTrue(fit.isdisjoint(validation) and fit.isdisjoint(test) and validation.isdisjoint(test))
        trials=pd.read_csv(ROOT/'reports/boosting/validation_trials.csv')
        self.assertEqual(len(trials),30)
        self.assertTrue(trials.trees.between(1,1000).all())
    def test_macro_scores_match_held_out_predictions(self):
        from sklearn.metrics import mean_absolute_error,root_mean_squared_error,r2_score
        pred=pd.read_csv(ROOT/'reports/boosting/predictions.csv')
        summary=pd.read_csv(ROOT/'reports/boosting/metrics_summary.csv').set_index('model')
        for name,part in pred.groupby('model'):
            scores=[]
            for _,group in part.groupby('battery'):
                scores.append([mean_absolute_error(group.actual_soh,group.predicted_soh),root_mean_squared_error(group.actual_soh,group.predicted_soh),r2_score(group.actual_soh,group.predicted_soh)])
            np.testing.assert_allclose(np.mean(scores,axis=0),summary.loc[name,['mae','rmse','r2']].to_numpy(dtype=float),rtol=1e-8)
    def test_contributions_sum_to_prediction(self):
        import joblib
        from explanation import prediction_contributions
        sample=pd.read_csv(ROOT/'reports/features.csv').iloc[[0]][FEATURES]
        for name in ['catboost','xgboost']:
            artifact=joblib.load(ROOT/f'artifacts/boosting/{name}.joblib')
            estimator=artifact['model']
            baseline,effects,method=prediction_contributions(estimator,sample)
            self.assertIn('SHAP',method)
            self.assertAlmostEqual(baseline+effects.contribution.sum(),float(estimator.predict(sample)[0]),places=3)
    def test_app_evaluation_and_sample_prediction(self):
        from streamlit.testing.v1 import AppTest
        from unittest.mock import patch
        history_guard=patch('history_store.save_results')
        history_guard.start();self.addCleanup(history_guard.stop)
        app=AppTest.from_file(str(ROOT/'app/streamlit_app.py'),default_timeout=60).run()
        for name in ['CatBoost','XGBoost']:
            app.radio(key='navigation').set_value('Đánh giá mô hình').run()
            app.selectbox(key='evaluation_model').set_value(name).run()
            self.assertFalse(app.exception or app.error,[e.message for e in app.exception])
            app.radio(key='navigation').set_value('Dự đoán SOH').run()
            app.selectbox(key='soh_model').set_value(name).run()
            app.checkbox[0].check().run();app.button[0].click().run()
            self.assertFalse(app.exception or app.error,[e.message for e in app.exception])
            self.assertEqual(app.session_state['prediction_history'][-1]['model'],name)
if __name__=='__main__': unittest.main()
