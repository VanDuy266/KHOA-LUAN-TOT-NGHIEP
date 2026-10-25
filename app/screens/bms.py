"""Actual on-road BMS experiment; derived field labels are explicitly identified."""
import io
import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from app_data import ROOT,table,metadata,_model
from components import heading,section,stat,number,csv_download,note
from charts import finish
from labels import MODEL_NAMES
from battery_soh.bms import FEATURES,charging_features

DISPLAY={'model':'Mô hình','vehicle':'Xe','session':'Phiên sạc','start':'Bắt đầu sạc',
         'reference_soh_pct':'SOH suy ra (%)','prediction':'SOH dự đoán (%)',
         'reference_capacity_ah':'Dung lượng suy ra (Ah)','month':'Tháng',
         'reference_sessions':'Phiên tạo nhãn','mae':'MAE (điểm %)',
         'rmse':'RMSE (điểm %)','r2':'R²','fold':'Vòng kiểm thử',
         'fit_seconds':'Thời gian học (s)','predict_seconds':'Thời gian dự đoán (s)',
         'n_train':'Mẫu học','n_test':'Mẫu kiểm thử'}

def shown(data):
    data=data.copy()
    if 'model' in data: data['model']=data.model.map(MODEL_NAMES).fillna(data.model)
    return data.rename(columns=DISPLAY)

def render():
    heading('THỰC NGHIỆM TRÊN XE','Dữ liệu BMS trên xe','BAIC EU500 · CATL NCM · bộ pin 145 Ah · dữ liệu sạc qua CAN')
    if not (ROOT/'reports/bms/dataset_summary.json').exists():
        st.info('Dữ liệu BMS đang được xử lý; chưa có kết quả để hiển thị.');return
    info=metadata('reports/bms/dataset_summary.json')
    for col,item in zip(st.columns(4),[
        ('XE THỰC TẾ',str(info['vehicles']),'Giữ riêng mã xe khi kiểm thử'),
        ('BẢN GHI NGUỒN',number(info['raw_rows']),'Dữ liệu sạc; bước đo khoảng 8 giây'),
        ('PHIÊN ĐÁNH GIÁ',number(info['sessions']),'Cửa sổ tín hiệu đầu sạc 120 giây'),
        ('DUNG LƯỢNG BỘ PIN','145 Ah','90 cell nối tiếp · 32 cảm biến nhiệt')]):
        with col: stat(*item)
    note('Cách hiểu kết quả BMS',
         'Đây là dữ liệu của xe vận hành thực tế. Nhãn SOH được suy ra từ dòng điện và SOC trong các phiên sạc, '
         'không phải phép đo dung lượng độc lập trong phòng thử nghiệm. Điểm số thể hiện mức khớp với nhãn suy ra. '
         'Mô hình BMS được huấn luyện riêng, không sử dụng trực tiếp mô hình SDU cho cell 2,4 Ah.',kind='soft')
    mode=st.radio('Nội dung BMS',['Dữ liệu trên xe','Đánh giá theo xe','Dự đoán BMS','Nguồn và phương pháp'],horizontal=True,key='bms_mode')
    st.caption(f"{info['monthly_labels']} nhãn xe–tháng dùng cho {number(info['sessions'])} phiên; các phiên trong cùng tháng có chung nhãn, không phải từng ấy phép đo SOH độc lập.")
    data=table('reports/bms/features.csv')
    if mode=='Dữ liệu trên xe':
        vehicle=st.selectbox('Xe cần xem',sorted(data.vehicle.unique()),key='bms_vehicle')
        reference=table('reports/bms/monthly_reference.csv').query('vehicle == @vehicle').copy()
        reference['soh']=reference.reference_capacity_ah/145*100
        section('01','Diễn biến SOH suy ra','Trung vị theo tháng · có ít nhất 3 phiên đạt điều kiện trong tháng')
        chart=alt.Chart(reference).mark_line(point=True,color='#087f79').encode(
            x=alt.X('month:O',title='Tháng'),y=alt.Y('soh:Q',title='SOH suy ra (%)',scale=alt.Scale(zero=False)),
            tooltip=['month',alt.Tooltip('soh:Q',format='.2f'), 'reference_sessions'])
        st.altair_chart(finish(chart),width='stretch',theme=None)
        section('02','Tín hiệu đầu phiên sạc','Điện áp bộ pin và điện áp cell được lưu riêng')
        sessions=data[data.vehicle==vehicle]
        session_names=sessions.set_index('session').start.to_dict()
        selected=st.selectbox('Phiên sạc',sessions.session.tolist(),format_func=lambda s: f"{int(s)} · {session_names[s]}",key='bms_session')
        windows=pd.read_parquet(ROOT/'data/bms/processed/windows.parquet',filters=[('vehicle','=',vehicle),('session','=',int(selected))])
        channel=st.selectbox('Tín hiệu',['pack_voltage','charge_current','max_temperature','min_cell_voltage','max_cell_voltage'],
            format_func=lambda x:dict(pack_voltage='Điện áp bộ pin (V)',charge_current='Dòng điện nguồn (A) · sạc âm',max_temperature='Nhiệt độ lớn nhất (°C)',min_cell_voltage='Điện áp cell nhỏ nhất (V)',max_cell_voltage='Điện áp cell lớn nhất (V)')[x])
        st.altair_chart(finish(alt.Chart(windows).mark_line(point=True,color='#087f79').encode(
            x=alt.X('time_s:Q',title='Giây từ đầu sạc'),y=alt.Y(f'{channel}:Q',title=channel,scale=alt.Scale(zero=False)),tooltip=['time_s',channel])),width='stretch',theme=None)
        st.dataframe(shown(reference.drop(columns='soh')).round(3),hide_index=True,width='stretch')
        csv_download('Tải nhãn suy ra theo tháng',shown(reference.drop(columns='soh')),f'{vehicle}_nhan_thang.csv')
    elif mode=='Đánh giá theo xe':
        section('01','Kiểm thử xe chưa được học','5 vòng GroupKFold · chia theo xe, không chia ngẫu nhiên các dòng đo')
        metrics=table('reports/bms/metrics_summary.csv').set_index('model').loc[['Ridge-RF residual','Random Forest','Ridge','Mean baseline']].reset_index()
        st.dataframe(shown(metrics).round(3),hide_index=True,width='stretch')
        st.caption('MAE/RMSE là điểm phần trăm của SOH suy ra. Chỉ số lấy trung bình đều theo xe; không so trực tiếp với MAE SDU vì nhãn và điều kiện khác nhau.')
        model=st.selectbox('Mô hình BMS cần xem',metrics.model.tolist(),format_func=lambda x:MODEL_NAMES.get(x,x),key='bms_evaluation_model')
        predictions=table('reports/bms/predictions.csv')
        vehicles=sorted(predictions.vehicle.unique())
        vehicle=st.selectbox('Xe kiểm thử',vehicles,key='bms_test_vehicle')
        part=predictions[(predictions.model==model)&(predictions.vehicle==vehicle)].sort_values('start')
        # Aggregate only for legible display; metrics remain computed on held-out sessions.
        line=part.groupby('month')[['reference_soh_pct','prediction']].mean().reset_index().melt('month',var_name='kind',value_name='soh')
        line['kind']=line.kind.map({'reference_soh_pct':'Nhãn SOH suy ra','prediction':'Dự đoán xe giữ riêng'})
        st.altair_chart(finish(alt.Chart(line).mark_line(point=True).encode(x=alt.X('month:O',title='Tháng'),
            y=alt.Y('soh:Q',title='SOH suy ra (%)',scale=alt.Scale(zero=False)),color=alt.Color('kind:N',title=None),tooltip=['month','kind',alt.Tooltip('soh:Q',format='.2f')])),width='stretch',theme=None)
        st.dataframe(shown(table('reports/bms/metrics_by_vehicle.csv').query('model == @model')).round(3),hide_index=True,width='stretch')
        with st.expander('Thời gian huấn luyện và dự đoán'):
            st.dataframe(shown(table('reports/bms/timings.csv').query('model == @model')).round(3),hide_index=True,width='stretch')
        csv_download('Tải dự đoán xe giữ riêng',shown(part),'bms_kiem_thu_theo_xe.csv')
    elif mode=='Dự đoán BMS':
        section('01','Ước lượng từ đầu phiên sạc','Chỉ dùng mô hình đã học từ dữ liệu BMS BAIC cùng cấu hình')
        name=st.selectbox('Mô hình BMS',['Ridge-RF residual','Random Forest'],format_func=lambda x:MODEL_NAMES[x],key='bms_predict_model')
        origin=st.radio('Dữ liệu đầu vào',['Phiên minh họa','CSV BMS cùng cấu hình'],horizontal=True,key='bms_input')
        window=None
        if origin=='Phiên minh họa':
            vehicle=st.selectbox('Xe minh họa',sorted(data.vehicle.unique()),key='bms_demo_vehicle')
            sid=int(data[data.vehicle==vehicle].session.iloc[0])
            window=pd.read_parquet(ROOT/'data/bms/processed/windows.parquet',filters=[('vehicle','=',vehicle),('session','=',sid)])
            st.caption('Phiên này đã dùng học lại mô hình bàn giao; kết quả chỉ để minh họa. Xem Đánh giá theo xe để lấy kết quả giữ riêng.')
        else:
            st.caption('CSV cần time_s, soc, pack_voltage, charge_current, max_cell_voltage, min_cell_voltage, max_temperature, min_temperature. Đơn vị: giây, %, V, A, °C; sạc mang dấu âm. Chỉ nhận cấu hình BAIC 145 Ah; không dùng cho xe khác chỉ vì trùng tên cột.')
            upload=st.file_uploader('CSV đầu phiên sạc BMS',type=['csv'],key='bms_upload')
            template=ROOT/'data/bms/processed/01_example.csv.gz'
            if template.exists(): csv_download('Tải CSV mẫu theo đúng cột',pd.read_csv(template).query('time_s <= 120'),'bms_cua_so_120s.csv')
            if upload is not None:
                try:
                    if upload.size>10*1024*1024: raise ValueError('CSV vượt giới hạn 10 MiB')
                    window=pd.read_csv(io.BytesIO(upload.getvalue()))
                except (ValueError,UnicodeError) as e: st.error(f'Không đọc được CSV: {e}')
        if st.button('Dự đoán BMS',type='primary',key='bms_predict'):
            try:
                if window is None: raise ValueError('Chọn hoặc tải dữ liệu đầu vào trước')
                required=['time_s','soc','pack_voltage','charge_current','max_cell_voltage','min_cell_voltage','max_temperature','min_temperature']
                if not set(required)<=set(window): raise ValueError('CSV chưa đủ các cột bắt buộc')
                window=window[required].apply(pd.to_numeric,errors='raise')
                if not np.isfinite(window).all().all(): raise ValueError('CSV chứa giá trị thiếu hoặc vô hạn')
                if (window.time_s.diff().dropna()<=0).any() or (window.time_s.diff().dropna()>10).any(): raise ValueError('Thời gian trùng, đi lùi hoặc gián đoạn quá 10 giây')
                if abs(window.time_s.iloc[0])>1e-6: raise ValueError('Thời gian phải bắt đầu từ 0 ở đầu phiên sạc')
                window=window[window.time_s<=120]
                if len(window)<12 or window.time_s.max()<112: raise ValueError('Chưa đủ cửa sổ đầu sạc 120 giây')
                if not window.soc.between(0,100).all(): raise ValueError('SOC phải nằm trong 0–100%')
                if (window.soc.diff().dropna() < -0.1).any() or (window.soc.diff().dropna() > 2).any(): raise ValueError('SOC đi lùi hoặc nhảy quá mức cho phép của quy trình BMS')
                if not window.pack_voltage.between(200,450).all(): raise ValueError('Điện áp bộ pin ngoài phạm vi kiểm tra 200–450 V')
                if not window.charge_current.between(-300,0).all() or (window.charge_current<0).mean()<.95: raise ValueError('Cần dòng sạc âm, đúng quy ước nguồn')
                if not window.min_cell_voltage.between(2,4.5).all() or not window.max_cell_voltage.between(2,4.5).all() or (window.max_cell_voltage<window.min_cell_voltage).any(): raise ValueError('Điện áp cell không hợp lệ')
                if not window.min_temperature.between(-30,85).all() or not window.max_temperature.between(-30,85).all() or (window.max_temperature<window.min_temperature).any(): raise ValueError('Nhiệt độ không hợp lệ')
                filename='ridge_residual_forest.joblib' if name=='Ridge-RF residual' else 'random_forest.joblib'
                path=ROOT/'artifacts/bms'/filename
                fitted=_model(str(path),path.stat().st_mtime_ns)
                features=pd.DataFrame([charging_features(window)])[FEATURES]
                low=pd.Series(fitted['training_min']);high=pd.Series(fitted['training_max'])
                outside=((features.iloc[0]<low)|(features.iloc[0]>high))
                prediction=float(fitted['model'].predict(features)[0])
                stat('SOH SUY RA · ƯỚC LƯỢNG',f'{prediction:.2f} %','Nhãn dung lượng vận hành / 145 Ah; chưa đối chiếu RPT độc lập',accent=True)
                if outside.any(): st.info('Đặc trưng ngoài miền học: '+', '.join(outside[outside].index))
                csv_download('Tải kết quả BMS', pd.DataFrame([{'Mô hình':MODEL_NAMES[name], 'SOH suy ra ước lượng (%)':prediction, 'Dung lượng danh định (Ah)':145, 'Loại nhãn':'Suy ra từ vận hành; chưa đối chiếu RPT', 'Số đặc trưng ngoài miền':int(outside.sum())}]), 'bms_du_doan.csv')
                st.caption('Không dùng kết quả này để kết luận an toàn hoặc xác nhận SOH vật lý của xe khác.')
            except (ValueError,KeyError,TypeError,OSError) as e: st.error(f'Chưa dự đoán được: {e}')
    else:
        section('01','Nguồn công bố','Deng và cộng sự · Applied Energy 339 (2023), 120954')
        st.link_button('Kho dữ liệu của tác giả','https://github.com/BatICM/battery-charging-data-of-on-road-electric-vehicles')
        st.link_button('Bài báo và phương pháp tạo nhãn','https://doi.org/10.1016/j.apenergy.2023.120954')
        st.write('20 xe BAIC EU500 dùng pin CATL NCM, 90 cell nối tiếp và 32 cảm biến nhiệt. Tín hiệu do thiết bị sạc nhận qua CAN; chu kỳ ghi khoảng 8 giây, thời gian theo dõi khoảng 29 tháng. Không phải dữ liệu XJTU đổi tên.')
        section('02','Nhãn dung lượng suy ra','Đây là đại lượng tham chiếu suy ra từ vận hành, có sai số của dòng điện và SOC')
        st.latex(r'Q_{suy\ ra}=\frac{\int -I(t)\,dt/3600}{\Delta SOC/100},\qquad SOH_{suy\ ra}=\frac{\mathrm{median}_{tháng}(Q)}{145}\times100')
        st.write('Quy trình ở đây lấy đầu vào trong 120 giây đầu sạc. Để giảm chồng lấn tín hiệu tạo nhãn, tích phân dòng chỉ lấy phần sau 120 giây, có ít nhất 100 mẫu và độ tăng SOC ít nhất 20 điểm %. Nhãn tháng cần ít nhất 3 phiên đạt điều kiện. Đây là điều chỉnh có công bố so với mã gốc, không phải tái tạo nguyên kết quả bài báo.')
        st.write('Loại phiên ngắn, thời gian gián đoạn, SOC đi lùi/nhảy, giá trị không hợp lệ hoặc không đủ phần sạc tạo nhãn. Không dùng available_capacity, available_energy, nhãn, thời gian lịch hay mã xe làm đặc trưng. Mô hình học riêng trên BMS; các mẫu cùng xe luôn ở cùng phía trong 5 vòng kiểm thử.')
        st.caption('Chưa có phép đo dung lượng RPT độc lập; chưa chứng minh chuyển giao từ SDU, độ chính xác SOH thực hoặc hiệu quả trên xe tại Việt Nam. Dữ liệu công bố chỉ có sạc, không phải toàn bộ hành trình chạy xe.')
        audit=pd.DataFrame(info['audit']).drop(columns='excluded')
        st.dataframe(audit,hide_index=True,width='stretch')
        csv_download('Tải kiểm tra dữ liệu nguồn',audit,'bms_kiem_tra_nguon.csv')

