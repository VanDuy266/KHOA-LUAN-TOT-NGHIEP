import unittest
import pandas as pd
from scripts.audit_thesis_results import audit, score

class ThesisAuditTests(unittest.TestCase):
    def setUp(self):
        self.data=pd.DataFrame(dict(vehicle=["A","A","B","B"],session=[1,2,1,2],target=[80.,90.,70.,90.]))
        self.pred=self.data.rename(columns={"target":"actual"}).assign(predicted=[81.,88.,71.,87.],fold=[1,1,2,2],model="M")
        self.folds=pd.Series({"A":1,"B":2})
        values=pd.DataFrame([score(g) for _,g in self.pred.groupby("vehicle")]).mean().to_dict()
        self.report=pd.DataFrame([dict(model="M",**values)])
    def run_audit(self,pred=None,report=None):
        return audit(self.data,self.pred if pred is None else pred,"vehicle",["vehicle","session"],"target",self.folds,self.report if report is None else report)
    def test_valid_coverage_and_macro(self):
        summary,groups=self.run_audit()
        self.assertEqual(len(groups),2)
        self.assertAlmostEqual(summary.iloc[0].macro_mae,1.75)
    def test_reject_duplicate(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            self.run_audit(pd.concat([self.pred,self.pred.iloc[:1]]))
    def test_reject_missing_sample(self):
        with self.assertRaisesRegex(ValueError,"coverage"):
            self.run_audit(self.pred.iloc[:-1])
    def test_reject_wrong_fold(self):
        p=self.pred.copy();p.loc[0,"fold"]=2
        with self.assertRaisesRegex(ValueError,"fold mismatch"):self.run_audit(p)
    def test_reject_wrong_label(self):
        p=self.pred.copy();p.loc[0,"actual"]=99
        with self.assertRaisesRegex(ValueError,"label mismatch"):self.run_audit(p)
    def test_reject_wrong_published_metric(self):
        p=self.report.copy();p.loc[0,"mae"]=0
        with self.assertRaisesRegex(ValueError,"score mismatch"):self.run_audit(report=p)

class ThesisAuditWebTests(unittest.TestCase):
    def test_results_and_downloads(self):
        from webapp.server import app
        client=app.test_client()
        r=client.get('/api/thesis-audit')
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json['status'],'passed')
        self.assertEqual(len(r.json['sdu']),8)
        self.assertEqual(len(r.json['bms']),4)
        for kind in ['report','defense','sdu','bms','paired','verification']:
            with client.get('/api/download/thesis-audit?kind='+kind) as r:
                self.assertEqual(r.status_code,200)
                self.assertIn('attachment',r.headers['Content-Disposition'])
        self.assertEqual(client.get('/api/download/thesis-audit?kind=../server.py').status_code,400)

if __name__=="__main__":unittest.main()
