# 배포용 백엔드 이미지. PDF export(services/export_pdf.py) 는 reportlab(순수 파이썬,
# 한글 폰트는 app/assets/fonts 에 임베드)이라 별도 시스템 라이브러리가 필요 없다
# — 이 이미지는 Cloud Run 같은 컨테이너 호스팅용 참고 구성일 뿐, apt 패키지 추가는
# 불필요하다. 참고: specs/QUOTE-1/tech/09-export.md
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
