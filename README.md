# Local RAG System with Mistral and Ollama

A Retrieval-Augmented Generation (RAG) system that uses local Mistral model via Ollama for text generation, with FAISS for efficient vector search.

## Features

- Document processing for PDF, DOCX, and TXT files
- Text chunking with configurable size and overlap
- Vector embeddings using Google Gemini API
- Efficient similarity search with FAISS
- REST API with FastAPI
- Modern React frontend with Tailwind CSS
- Document upload and chat interface
- Context-aware responses with source attribution

## Prerequisites

- Python 3.8+
- Node.js 16+
- [Ollama](https://ollama.ai/) installed and running
- Mistral model downloaded in Ollama (run `ollama pull mistral`)

## Setup

### Local Development

1. Clone the repository:
   ```bash
   git clone https://github.com/Mohankirushna/RAG.git
   cd RAG
   ```

2. Set up the backend:
   ```bash
   # Create and activate a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install backend dependencies
   pip install -r requirements.txt
   ```

3. Set up the frontend:
   ```bash
   cd frontend
   npm install
   cd ..
   ```

4. Start the backend server:
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

5. Start the frontend development server:
   ```bash
   cd frontend
   npm start
   ```

## Deployment

### Backend Deployment (Render)

1. Push your code to GitHub
2. Go to [Render](https://render.com) and sign up/login
3. Click "New" → "Web Service"
4. Connect your GitHub repository
5. Configure:
   - **Name**: rag-backend
   - **Region**: Choose the closest to your users
   - **Branch**: main
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Environment Variables**:
     - `MODEL_NAME=mistral`
     - `OLLAMA_API_BASE_URL=http://localhost:11434` (or your Ollama server URL)
     - `UPLOAD_DIR=./uploads`
     - `INDEX_DIR=./indices`

### Frontend Deployment (Vercel)

1. Go to [Vercel](https://vercel.com) and sign up/login
2. Click "Add New" → "Project"
3. Import your GitHub repository
4. Configure:
   - **Framework Preset**: Create React App
   - **Build Command**: `cd frontend && npm install && npm run build`
   - **Output Directory**: `frontend/build`
   - **Environment Variables**:
     - `REACT_APP_API_URL`: Your deployed backend URL (e.g., `https://rag-backend.onrender.com`)

### Environment Variables

Create a `.env` file in the root directory with the following variables:

```
# Backend
MODEL_NAME=mistral
OLLAMA_API_BASE_URL=http://localhost:11434
UPLOAD_DIR=./uploads
INDEX_DIR=./indices

# Frontend (for local development)
REACT_APP_API_URL=http://localhost:8000
```

## Development

### Running Tests

To run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/
```

### Building for Production

To build the frontend for production:

```bash
cd frontend
npm run build
```

This will create a production build in the `frontend/build` directory.

## Troubleshooting

### Common Issues

1. **Ollama Service Not Running**
   - Make sure Ollama is running: `ollama serve`
   - Verify the model is downloaded: `ollama list`

2. **Port Conflicts**
   - If port 8000 is in use, update the port in `backend/main.py` and `frontend/.env`

3. **Missing Dependencies**
   - Run `pip install -r requirements.txt` to ensure all Python dependencies are installed
   - Run `cd frontend && npm install` to install frontend dependencies

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Ollama](https://ollama.ai/) for the local LLM server
- [FAISS](https://github.com/facebookresearch/faiss) for efficient similarity search
- [FastAPI](https://fastapi.tiangolo.com/) for the backend API
- [React](https://reactjs.org/) for the frontend

## Running the Application

### Backend

Start the FastAPI server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Frontend

In a new terminal, start the React development server:
```bash
cd frontend
npm start
```

The frontend will be available at `http://localhost:3000`

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /upload` - Upload and index a document
- `POST /query` - Query the RAG system
- `GET /documents/count` - Get document count
- `DELETE /documents` - Clear all documents (for testing)

## Example API Usage

### Upload a Document

```bash
curl -X 'POST' \
  'http://localhost:8000/upload' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@document.pdf;type=application/pdf' \
  -F 'metadata={"title":"Example Document"};type=application/json'
```

### Query the RAG System

```bash
curl -X 'POST' \
  'http://localhost:8000/query' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "What is this document about?",
    "top_k": 3
  }'
```

## Persisting FAISS Index

The FAISS index is automatically saved to the `indices` directory when documents are added. To persist the index between server restarts, make sure the `indices` directory exists and is writable.

## Frontend Features

- Drag and drop document upload
- Real-time chat interface
- Document management
- Responsive design
- Syntax highlighting for code blocks
- Source attribution for answers

## License

This project is licensed under the MIT License - see the LICENSE file for details.
