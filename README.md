# prometheus_nhn_rds
프로메테우스를 이용한 NHN 클라우드 RDS 모니터링 지표 수집.

# Docker Build

docker build --platform linux/amd64 -t prometheus_nhn_rds_<port> .

# Docker Ops.
docker run -d \
  -e ACCESS_KEY="" \
  -e SECRET_KEY= "" \
  -e APP_KEY= "" \
  -e RDS_ID="" \
  -e PORT= \
  -p: \
  --name \