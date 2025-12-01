# Stage 1: Build Frontend
FROM node:20-alpine as frontend-build
WORKDIR /app/frontend
COPY crane-web-app/frontend/package*.json ./
RUN npm install
COPY crane-web-app/frontend ./
RUN npm run build

# Stage 2: Backend Runtime
FROM python:3.11-slim
WORKDIR /app

# Copy backend requirements and install
COPY crane-web-app/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY crane-web-app/backend ./crane-web-app/backend

# Copy built frontend assets
# main.py expects ../frontend/dist relative to itself.
COPY --from=frontend-build /app/frontend/dist ./crane-web-app/frontend/dist

# Set working directory to backend so imports work naturally
WORKDIR /app/crane-web-app/backend

# Expose port
EXPOSE 10000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
