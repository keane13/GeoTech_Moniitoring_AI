USE DATABASE GEOTECH;
USE SCHEMA CORE;

-- Tarik perubahan dan file environment.yml terbaru dari GitHub
ALTER GIT REPOSITORY GEOTECH.CORE.GEOTECH_MONIITORING_AI FETCH;
-- Buat ulang aplikasinya
CREATE OR REPLACE STREAMLIT GEOTECH.CORE.GEOTECH_APP
  ROOT_LOCATION = '@GEOTECH.CORE.GEOTECH_MONIITORING_AI/branches/main/streamlit'
  MAIN_FILE = 'streamlit_app.py'
  QUERY_WAREHOUSE = COMPUTE_WH;
  -- (Pastikan 'COMPUTE_WH' adalah nama warehouse yang aktif di Snowflake Anda)
