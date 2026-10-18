"""Các thành phần trình bày nhỏ dùng chung cho các màn hình."""
from html import escape
import streamlit as st


def number(value):
    return f"{int(value):,}".replace(",", ".")


def heading(kicker, title, description):
    st.markdown(f'<div class="page-heading"><div class="eyebrow">{escape(kicker)}</div>'
                f'<h1>{escape(title)}</h1><p>{escape(description)}</p></div>', unsafe_allow_html=True)


def section(number_text, title, description=""):
    st.markdown(f'<div class="section-heading"><span>{escape(number_text)}</span>'
                f'<div><h3>{escape(title)}</h3><p>{escape(description)}</p></div></div>', unsafe_allow_html=True)


def stat(label, value, detail, accent=False):
    variant = " stat-accent" if accent else ""
    st.markdown(f'<div class="stat-card{variant}"><div class="stat-label">{escape(label)}</div>'
                f'<div class="stat-value">{escape(str(value))}</div><div class="stat-detail">{escape(detail)}</div></div>',
                unsafe_allow_html=True)


def note(title, text, kind="plain"):
    st.markdown(f'<div class="note note-{kind}"><strong>{escape(title)}</strong>'
                f'<p>{escape(text)}</p></div>', unsafe_allow_html=True)


def csv_download(label, frame, filename, key=None):
    # BOM giúp Excel trên Windows đọc đúng tên cột tiếng Việt.
    st.download_button(label, frame.to_csv(index=False).encode("utf-8-sig"), filename,
                       "text/csv", key=key, icon=":material/download:")
