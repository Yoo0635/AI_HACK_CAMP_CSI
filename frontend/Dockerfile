# frontend/Dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# 5173 포트 개방
EXPOSE 5173

# 도커 환경에서 외부 접속이 가능
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]