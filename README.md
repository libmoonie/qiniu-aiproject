# qiniu-aiproject
AI英语口语陪练

## 项目介绍
本项目对接Ollama本地大模型，前端页面实现用户提问，后端调用127.0.0.1:11434接口获取AI回复，使用qwen2.5:3b本地模型，离线可用、无需付费API。

## 环境依赖
1. Windows系统
2. 已安装Ollama
3. 本地提前拉取模型：qwen2.5:3b

## 部署步骤
### 1. 安装Ollama
下载安装包安装Ollama软件，配置国内镜像加速。
### 2. 拉取AI模型
打开终端执行：
```bash
ollama pull qwen2.5:3b

## **启动项目**
cd backend
npm install
npm run start
cd frontend
npm install
npm run dev
