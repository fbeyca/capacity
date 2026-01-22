import streamlit as st
import pandas as pd
import math
import plotly.graph_objects as go
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. VERİLER VE YAPILANDIRMA
# -----------------------------------------------------------------------------

# Mevcut müfredat saatleri
BASE_CURRICULUM = {
    'Bilgisayar': {1: 28, 2: 25, 3: 23, 4: 18, 5: 17, 6: 21, 7: 15, 8: 15},
    'Gida':       {1: 27, 2: 26, 3: 25, 4: 23, 5: 15, 6: 21, 7: 16, 8: 15},
    'Sanayi':     {1: 22, 2: 22, 3: 18, 4: 18, 5: 18, 6: 17, 7: 14, 8: 14}
}

# Mevcut Öğrenci Sayıları
CURRENT_STUDENTS = {
    'Bilgisayar': {'Hazirlik': 46, 1: 32, 2: 7, 3: 0, 4: 0},
    'Gida':       {'Hazirlik': 11, 1: 21, 2: 2, 3: 0, 4: 0},
    'Sanayi':     {'Hazirlik': 20, 1: 28, 2: 0, 3: 0, 4: 0}
}

ROOMS_DATA = [
    {'Sinif': '208', 'Kapasite': 30}, {'Sinif': '209', 'Kapasite': 30},
    {'Sinif': '205', 'Kapasite': 40}, {'Sinif': '213', 'Kapasite': 30},
    {'Sinif': '204', 'Kapasite': 40}, {'Sinif': '203', 'Kapasite': 40},
    {'Sinif': '202', 'Kapasite': 100}, {'Sinif': '201', 'Kapasite': 80},
    {'Sinif': '303', 'Kapasite': 100}, {'Sinif': '316', 'Kapasite': 30},
    {'Sinif': '306', 'Kapasite': 40}, {'Sinif': '307', 'Kapasite': 40},
    {'Sinif': '314', 'Kapasite': 40}, {'Sinif': '313', 'Kapasite': 40},
    {'Sinif': '312', 'Kapasite': 30}, {'Sinif': '412', 'Kapasite': 40},
    {'Sinif': '413', 'Kapasite': 40}, {'Sinif': '415', 'Kapasite': 30},
    {'Sinif': '406', 'Kapasite': 30}
]
TOTAL_ROOMS = len(ROOMS_DATA)

# -----------------------------------------------------------------------------
# 2. HESAPLAMA MOTORU
# -----------------------------------------------------------------------------

def project_students(years, intake_plan, prep_pass_rate, depts):
    projection = {0: {d: CURRENT_STUDENTS.get(d, {'Hazirlik': 0, 1: 0, 2: 0, 3: 0, 4: 0}) for d in depts}}
    
    for y in range(1, years + 1):
        prev_year_data = projection[y-1]
        current_year_data = {d: {} for d in depts}
        year_intake = intake_plan[intake_plan['Yıl'] == y].iloc[0]
        
        for dept in depts:
            new_students = year_intake.get(dept, 0)
            direct_to_first = new_students * prep_pass_rate
            stay_in_prep = new_students * (1 - prep_pass_rate)
            from_prev_prep = prev_year_data[dept].get('Hazirlik', 0)
            
            current_year_data[dept]['Hazirlik'] = round(stay_in_prep)
            current_year_data[dept][1] = round(direct_to_first + from_prev_prep)
            current_year_data[dept][2] = prev_year_data[dept].get(1, 0)
            current_year_data[dept][3] = prev_year_data[dept].get(2, 0)
            current_year_data[dept][4] = prev_year_data[dept].get(3, 0)
            
        projection[y] = current_year_data
    return projection

def calculate_capacity(projection, prep_size, dept_size, curriculum):
    res = []
    for year, data in projection.items():
        prep_classes = 0
        total_dept_slots = 0
        for dept, classes in data.items():
            prep_classes += math.ceil(classes.get('Hazirlik', 0) / prep_size)
            for grade in [1, 2, 3, 4]:
                count = classes.get(grade, 0)
                if count <= 0: continue
                sem = (grade * 2) - 1
                weekly_h = curriculum.get(dept, BASE_CURRICULUM['Bilgisayar']).get(sem, 20)
                sections = math.ceil(count / dept_size)
                total_dept_slots += math.ceil((sections * weekly_h) / 3)
                
        res.append({
            'Yıl': year,
            'Hazırlık Oda İhtiyacı': prep_classes,
            'Bölüm Slot İhtiyacı': total_dept_slots,
            'Kalan Müsait Oda': TOTAL_ROOMS - prep_classes,
            'Mevcut Slot Kapasitesi': max(0, (TOTAL_ROOMS - prep_classes) * 15)
        })
    return pd.DataFrame(res)

# -----------------------------------------------------------------------------
# 3. UI
# -----------------------------------------------------------------------------

st.set_page_config(page_title="Kapasite Planlama", layout="wide")
st.title("🏗️ Yeni Bölüm Senaryolu Kapasite Planlama")

# --- SIDEBAR ---
st.sidebar.header("🚀 Yeni Bölüm Ayarları")
new_dept_count = st.sidebar.number_input("Açılacak Yeni Bölüm Sayısı", 0, 5, 0)

all_depts = list(CURRENT_STUDENTS.keys())
for i in range(new_dept_count):
    all_depts.append(f"Yeni Bölüm {i+1}")

# Dinamik Müfredat Sözlüğü
current_curriculum = BASE_CURRICULUM.copy()
for i in range(new_dept_count):
    current_curriculum[f"Yeni Bölüm {i+1}"] = BASE_CURRICULUM['Bilgisayar']

# Kontenjan Planı
st.sidebar.subheader("📋 Kontenjan Girişi")
default_plan_dict = {'Yıl': [1, 2, 3, 4, 5]}
for d in all_depts:
    if d in ['Bilgisayar']: default_plan_dict[d] = [60]*5
    elif d in ['Sanayi', 'Gida']: default_plan_dict[d] = [30]*5
    else: default_plan_dict[d] = [30]*5 # Yeni bölümler için varsayılan 30

edited_plan = st.sidebar.data_editor(pd.DataFrame(default_plan_dict), hide_index=True)

st.sidebar.markdown("---")
prep_pass = st.sidebar.slider("Hazırlık Atlama (%)", 0, 100, 10) / 100.0
util_target = st.sidebar.slider("Hedeflenen Slot Kullanım Verimliliği (%)", 50, 100, 80) / 100.0
prep_limit = st.sidebar.number_input("Hazırlık Max Mevcut", value=18)
dept_limit = st.sidebar.number_input("Bölüm Max Mevcut", value=40)

# --- ANALİZ ---
proj_data = project_students(5, edited_plan, prep_pass, all_depts)
cap_df = calculate_capacity(proj_data, prep_limit, dept_limit, current_curriculum)

# Verimlilik düzeltmesi (Hedeflenen doluluk oranına göre kapasiteyi düşürür)
cap_df['Efektif Kapasite'] = (cap_df['Mevcut Slot Kapasitesi'] * util_target).round(0)

# --- GRAFİKLER ---
t1, t2 = st.tabs(["👥 Öğrenci Tahmini", "🏢 Kapasite & Verimlilik"])

with t1:
    rows = []
    for y, d in proj_data.items():
        for dept, cls in d.items():
            rows.append({'Yıl': y, 'Bölüm': dept, 'Toplam': sum(cls.values())})
    st.plotly_chart(px.line(pd.DataFrame(rows), x='Yıl', y='Toplam', color='Bölüm', markers=True, title="Bölüm Bazlı Öğrenci Artışı"), use_container_width=True)

with t2:
    st.subheader("Slot Kapasite Dengesi")
    st.write(f"Şu anki hedef verimlilik: **%{int(util_target*100)}** (Ders çakışmaları ve planlama payı)")
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=cap_df['Yıl'], y=cap_df['Bölüm Slot İhtiyacı'], name='Slot Talebi'))
    fig.add_trace(go.Scatter(x=cap_df['Yıl'], y=cap_df['Efektif Kapasite'], name='Efektif Kapasite (Verimli)', line=dict(color='green', width=3)))
    fig.add_trace(go.Scatter(x=cap_df['Yıl'], y=cap_df['Mevcut Slot Kapasitesi'], name='Maksimum Teorik Kapasite', line=dict(color='red', dash='dot')))
    fig.update_layout(title="Haftalık Slot Talebi vs Kullanılabilir Kapasite")
    st.plotly_chart(fig, use_container_width=True)

    if any(cap_df['Bölüm Slot İhtiyacı'] > cap_df['Efektif Kapasite']):
        st.warning("⚠️ Planlanan verimlilik oranına göre kapasite yetersiz kalabilir. Çizelge oluştururken zorluk yaşanabilir.")

st.dataframe(cap_df)