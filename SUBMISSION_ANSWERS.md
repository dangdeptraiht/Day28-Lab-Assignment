# Lab 28 Submission Answers

## 1. Trade-offs kiến trúc

Thiết kế tách local infrastructure khỏi GPU serving. Local stack giữ Kafka, Prefect, Qdrant, Redis, Prometheus, Grafana và API Gateway để dễ debug, dễ chạy lại demo, và không phụ thuộc toàn bộ vào GPU. Kaggle chỉ phục vụ phần tốn compute là vLLM và embedding service. Trade-off là có thêm network latency qua tunnel, nhưng maintainability và chi phí tốt hơn vì phần stateful chạy local.

## 2. Xử lý mất kết nối Local + Kaggle

API Gateway đọc `VLLM_URL`/`VLLM_NGROK_URL` nếu có. Khi URL không cấu hình hoặc request vLLM lỗi, gateway trả lời bằng local fallback thay vì crash. Qdrant search cũng được bọc lỗi, nên nếu vector store tạm lỗi thì chat endpoint vẫn hoạt động với `context_count=0`.

## 3. Kafka decouple components như thế nào

Producer chỉ cần publish vào topic `data.raw`; Prefect consumer đọc topic và ghi batch sang Delta/Parquet. Nhờ vậy ingestion không phải gọi trực tiếp Feature Store, Vector Store, hoặc API Gateway. Kafka cũng cho replay dữ liệu, xử lý lại batch sau lỗi, và giảm coupling giữa tốc độ nhận dữ liệu với tốc độ xử lý downstream.

## 4. Observability

FastAPI Gateway expose `/metrics` qua `prometheus-fastapi-instrumentator`. Prometheus scrape `api-gateway:8000`, Grafana đọc metrics từ Prometheus, và health/readiness scripts kiểm tra các endpoint chính. LangSmith được hỗ trợ qua `LANGCHAIN_API_KEY`; script observability skip phần này nếu chưa cấu hình key để local demo vẫn chạy được.

## 5. Service crash và graceful degradation

Nếu Qdrant lỗi, gateway bỏ qua retrieval và tiếp tục trả lời. Nếu Kaggle/vLLM mất tunnel, gateway dùng local fallback. Redis và Kafka được kiểm tra bằng readiness script; Kafka topic `data.raw` được tạo lại bằng `--if-not-exists` trong readiness path. Với production thật, bước tiếp theo là thêm retry/backoff, circuit breaker có state, và persistent volumes/backup cho Redis/Qdrant.
