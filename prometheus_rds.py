from prometheus_client import start_http_server, Gauge
import time
import requests
import base64
from datetime import datetime, timedelta
import os

# NHN Cloud API Key 설정
ACCESS_KEY = os.getenv("ACCESS_KEY", "default_access_key")
SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
app_key = os.getenv("APP_KEY", "default_app_key")
rds_id = os.getenv("RDS_ID", "default_rds_id")

# API URL
OAUTH_URL = "https://oauth.api.nhncloudservice.com/oauth2/token/create"
STATISTICS_URL = "https://kr1-rds-mariadb.api.nhncloudservice.com/v3.0/metric-statistics"

# Prometheus Gauge 저장소
prometheus_gauges = {}

def get_auth_token():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {base64.b64encode(f'{ACCESS_KEY}:{SECRET_KEY}'.encode()).decode()}"
    }
    data = {"grant_type": "client_credentials"}
    response = requests.post(OAUTH_URL, headers=headers, data=data)
    response.raise_for_status()
    return response.json()["access_token"]

def get_metric_statistics(app_key, ACCESS_KEY, SECRET_KEY, access_token, instance_id, measure_names, from_time, to_time, interval=1):
    headers = {
        "X-TC-APP-KEY": app_key,
        "X-TC-AUTHENTICATION-ID": ACCESS_KEY,
        "X-TC-AUTHENTICATION-SECRET": SECRET_KEY,
        "Authorization": f"Bearer {access_token}"
    }
    params = {
        "dbInstanceId": instance_id,
        "measureNames": measure_names,
        "from": from_time,
        "to": to_time,
        "interval": interval
    }
    response = requests.get(STATISTICS_URL, headers=headers, params=params)
    response.raise_for_status()
    response_data = response.json()
    
    if not response_data.get("header", {}).get("isSuccessful", False):
        raise ValueError(f"API 요청 실패: {response_data['header']['resultMessage']}")
    
    return response_data

def convert_to_kst(timestamp):
    utc_time = datetime.utcfromtimestamp(timestamp)
    kst_time = utc_time + timedelta(hours=9)
    return kst_time.strftime('%Y-%m-%d %H:%M:%S')  # KST 형식 반환

def create_gauge_if_not_exists(metric_name, description=""):
    """Prometheus Gauge가 존재하지 않으면 생성."""
    if metric_name not in prometheus_gauges:
        prometheus_gauges[metric_name] = Gauge(metric_name.lower(), description)
    return prometheus_gauges[metric_name]

def fetch_and_update_metrics():
    try:
        # 인증 토큰 가져오기
        access_token = get_auth_token()

        # 시간 설정 (KST)
        to_time = datetime.utcnow() + timedelta(hours=9)
        from_time = to_time - timedelta(minutes=1)
        from_time = from_time.strftime('%Y-%m-%dT%H:%M:%S+09:00')
        to_time = to_time.strftime('%Y-%m-%dT%H:%M:%S+09:00')

        # 메트릭 데이터 가져오기
        instance_id = rds_id
        measure_names = [
            "QUERIES_PER_SEC", "SLOW_QUERY", "SLOW_QUERY_TOTAL",
            "CONNECTION_TOTAL", "CONNECTION_RUNNING", "CONNECTION_CACHED",
            "DATABASE_ACTIVITY_SELECT", "DATABASE_ACTIVITY_INSERT", "DATABASE_ACTIVITY_UPDATE",
            "DATABASE_ACTIVITY_REPLACE", "DATABASE_ACTIVITY_DELETE", "DATABASE_ACTIVITY_CALL",
            "INNODB_BUFFER_POOL_TOTAL_BYTES", "INNODB_BUFFER_POOL_USED_BYTES", "MYSQL_MAX_CONNECTIONS",
            "ROW_ACCESS_INDEX", "ROW_ACCESS_FULL_SCAN", "REPLICATION_DELAY",
            "MYSQL_CONNECTION_RATIO", "STORAGE_FREE_BYTE", "STORAGE_IO_READ",
            "STORAGE_IO_WRITE", "LOAD_AVG_1M", "LOAD_AVG_5M",
            "LOAD_AVG_15M", "MEMORY_FREE", "MEMORY_BUFFERS",
            "MEMORY_CACHED", "SWAP_USED", "SWAP_TOTAL",
            "STORAGE_USAGE", "STORAGE_USAGE_BYTE", "NETWORK_SENT",
            "NETWORK_RECV", "MEMORY_USAGE", "CPU_USAGE_BUSY",
            "CPU_USAGE_IDLE", "CPU_USAGE_IOWAIT", "CPU_USAGE_NICE",
            "CPU_USAGE_SYSTEM", "CPU_USAGE_USER", "CPU_USAGE"
        ]
        statistics = get_metric_statistics(app_key, ACCESS_KEY, SECRET_KEY, access_token, instance_id, measure_names, from_time, to_time)

        # 모든 메트릭 업데이트
        if "metricStatistics" in statistics:
            for metric in statistics["metricStatistics"]:
                metric_name = metric["measureName"]
                gauge = create_gauge_if_not_exists(metric_name)
                for value in metric["values"]:
                    timestamp, metric_value = value
                    # Prometheus Gauge 업데이트
                    gauge.set(float(metric_value))
        else:
            print("No metric statistics found!")

    except requests.exceptions.HTTPError as e:
        print(f"HTTP Error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")

if __name__ == "__main__":
    # Prometheus HTTP 서버 시작
    port = int(os.getenv("PORT", 8000))
    start_http_server(port)  # Prometheus는 http://localhost:8000/metrics 에서 데이터를 가져감
    print("Prometheus Exporter Running on Port...")

    # 주기적으로 메트릭 데이터 업데이트
    while True:
        fetch_and_update_metrics()
        time.sleep(60)  # 1분 간격으로 업데이트