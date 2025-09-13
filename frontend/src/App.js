import React, { useState, useEffect, useMemo, useRef } from 'react';
import { 
  PaperAirplaneIcon, 
  DocumentTextIcon, 
  XCircleIcon, 
  ArrowUpIcon, 
  ArrowPathIcon,
  Cog6ToothIcon,
  CheckCircleIcon,
  ExclamationCircleIcon
} from '@heroicons/react/24/outline';
import { useDropzone } from 'react-dropzone';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

// Configure API base URL
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Model status constants
const MODEL_STATUS = {
  LOADING: 'loading',
  READY: 'ready',
  ERROR: 'error'
};

function App() {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [modelStatus, setModelStatus] = useState(MODEL_STATUS.LOADING);
  const [modelError, setModelError] = useState(null);
  const [messages, setMessages] = useState([
    {
      id: 1,
      text: 'Initializing local Mistral model via Ollama...',
      sender: 'system',
      timestamp: new Date().toISOString(),
    },
  ]);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const messagesEndRef = useRef(null);

  // Scroll to bottom of chat when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle file drop
  const onDrop = (acceptedFiles) => {
    const newFiles = acceptedFiles.map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'pending',
    }));
    
    setUploadedFiles(prev => [...prev, ...newFiles]);
    
    // Upload files
    newFiles.forEach(uploadFile);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
    },
    multiple: true,
  });

  // Upload file to the server
  const uploadFile = async (fileItem) => {
    const formData = new FormData();
    formData.append('file', fileItem.file);
    
    setUploadedFiles(prev => 
      prev.map(item => 
        item.id === fileItem.id 
          ? { ...item, status: 'uploading' } 
          : item
      )
    );
    
    try {
      setIsUploading(true);
      const response = await axios.post(`${API_BASE_URL}/upload-pdf`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      console.log('Upload response:', response.data);
      
      setUploadedFiles(prev => 
        prev.map(item => 
          item.id === fileItem.id 
            ? { ...item, status: 'success', documentId: response.data.document_id } 
            : item
        )
      );
      
      // Add success message
      addMessage({
        text: `Successfully uploaded and indexed "${fileItem.name}" (${formatFileSize(fileItem.size)})`,
        sender: 'system',
      });
      
    } catch (error) {
      console.error('Upload error:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        statusText: error.response?.statusText,
        headers: error.response?.headers,
        config: error.config,
      });
      
      const errorMessage = error.response?.data?.detail || error.response?.data?.message || error.message || 'Upload failed';
      
      setUploadedFiles(prev => 
        prev.map(item => 
          item.id === fileItem.id 
            ? { ...item, status: 'error', error: errorMessage } 
            : item
        )
      );
    } finally {
      setIsUploading(false);
    }
  };

  // Check model status on component mount
  useEffect(() => {
    const checkModelStatus = async () => {
      try {
        // First check if backend is responding
        const healthResponse = await axios.get('http://localhost:8000/health');
        
        // Then check model status
        const response = await axios.get('http://localhost:8000/model-status');
        if (response.data.model_loaded) {
          setModelStatus(MODEL_STATUS.READY);
          setMessages(prev => {
            // Keep existing messages, just update the system message
            const otherMessages = prev.filter(msg => msg.sender !== 'system');
            return [
              ...otherMessages,
              {
                id: 1,
                text: 'Mistral model is ready. You can now upload documents and ask questions!',
                sender: 'system',
                timestamp: new Date().toISOString(),
              }
            ];
          });
        } else {
          setModelStatus(MODEL_STATUS.ERROR);
          setModelError('Mistral model is not loaded');
          setMessages(prev => {
            // Keep existing messages, just update the system message
            const otherMessages = prev.filter(msg => msg.sender !== 'system');
            return [
              ...otherMessages,
              {
                id: 1,
                text: 'Error: Mistral model is not loaded. Please make sure Ollama is running with the Mistral model.',
                sender: 'system',
                timestamp: new Date().toISOString(),
              }
            ];
          });
        }
      } catch (error) {
        console.error('Error checking model status:', error);
        setModelStatus(MODEL_STATUS.ERROR);
        setModelError('Failed to connect to the model service');
        setMessages(prev => {
          // Keep existing messages, just update the system message
          const otherMessages = prev.filter(msg => msg.sender !== 'system');
          return [
            ...otherMessages,
            {
              id: 1,
              text: 'Error: Could not connect to the local model service. Please make sure the backend server is running.',
              sender: 'system',
              timestamp: new Date().toISOString(),
            }
          ];
        });
      }
    };

    checkModelStatus();
    const interval = setInterval(checkModelStatus, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  // Handle query submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim() || isLoading || modelStatus !== MODEL_STATUS.READY) return;
    
    const userMessage = {
      id: Date.now(),
      text: query,
      sender: 'user',
      timestamp: new Date().toISOString(),
    };
    
    // Add user message immediately
    setMessages(prev => [...prev, userMessage]);
    setQuery('');
    setIsLoading(true);
    
    try {
      console.log('Sending query to:', `${API_BASE_URL}/query-pdf`);
      
      // Create a timeout promise
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Request timed out after 2 minutes')), 120000)
      );
      
      // Make the API call with a race between the request and the timeout
      const response = await Promise.race([
        axios.post(
          `${API_BASE_URL}/query-pdf`,
          { 
            query: userMessage.text,
            top_k: 3
          },
          {
            timeout: 120000, // 2 minute timeout
            headers: {
              'Content-Type': 'application/json',
            },
          }
        ),
        timeoutPromise
      ]);
      
      console.log('Received response:', response.data);
      
      // Ensure we have a valid response structure
      if (!response.data) {
        throw new Error('Empty response from server');
      }
      
      // Handle both response formats
      const answer = response.data.answer || 
                   (response.data.status === 'success' ? response.data.answer : null) || 
                   'No response generated';
      
      const contexts = response.data.contexts || [];
      
      const aiMessage = {
        id: Date.now() + 1,
        text: answer,
        sender: 'bot',
        timestamp: new Date().toISOString(),
        contexts: Array.isArray(contexts) ? contexts : [],
      };
      
      console.log('Created AI message:', aiMessage);
      setMessages((prev) => {
        console.log('Previous messages before adding bot message:', prev);
        const newMessages = [...prev, aiMessage];
        console.log('New messages after adding bot message:', newMessages);
        return newMessages;
      });
      
    } catch (error) {
      console.error('Query error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        statusText: error.response?.statusText,
        code: error.code,
        config: {
          url: error.config?.url,
          method: error.config?.method,
          data: error.config?.data
        }
      });
      
      let errorText = 'Sorry, there was an error processing your request.';
      
      if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
        errorText = 'The server is taking too long to respond. The model might be loading or processing a large document. Please try again in a moment.';
      } else if (error.response) {
        // Server responded with a status code outside 2xx
        errorText = `Server error (${error.response.status}): ${error.response.data?.error || error.response.statusText || 'Unknown error'}`;
      } else if (error.request) {
        // No response received
        errorText = 'Could not connect to the server. Please check if the backend service is running and try again.';
      }
      
      const errorMessage = {
        id: Date.now() + 1,
        text: errorText,
        sender: 'error',
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Render messages
  const renderMessages = useMemo(() => {
    console.log('Rendering messages:', messages);
    return messages.map((message, index) => {
      console.log(`Rendering message ${index}:`, message);
      console.log('Message type:', typeof message);
      console.log('Message keys:', message ? Object.keys(message) : 'null/undefined');
      return {
        id: message.id,
        text: message.text,
        sender: message.sender || 'system',
        timestamp: message.timestamp,
        ...message,
      };
    });
  }, [messages]);

  // Add a new message to the chat
  const addMessage = (message) => {
    setMessages((prev) => {
      // Check if message with this ID already exists
      if (prev.some(msg => msg.id === message.id)) {
        return prev;
      }
      return [...prev, {
        id: message.id || Date.now(),
        text: message.text,
        sender: message.sender || 'system',
        timestamp: message.timestamp || new Date().toISOString(),
        ...message
      }];
    });
  };
  
  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };
  
  // Clear all uploaded files
  const clearUploads = () => {
    setUploadedFiles([]);
  };
  
  // Toggle sidebar
  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sidebar */}
      <div className={`${isSidebarOpen ? 'w-80' : 'w-0'} bg-white border-r border-gray-200 flex flex-col transition-all duration-300 overflow-hidden`}>
        <div className="p-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-800">Documents</h2>
          <p className="text-sm text-gray-500">Upload and manage your documents</p>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4">
          <div 
            {...getRootProps()} 
            className={`p-6 border-2 border-dashed rounded-lg text-center cursor-pointer transition-colors ${
              isDragActive 
                ? 'border-blue-500 bg-blue-50' 
                : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'
            } mb-4`}
          >
            <input {...getInputProps()} />
            <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
            <p className="mt-2 text-sm text-gray-600">
              {isDragActive 
                ? 'Drop the files here...' 
                : 'Drag & drop files here, or click to select files'}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              PDF, DOCX, TXT (max 10MB)
            </p>
          </div>
          
          {uploadedFiles.length > 0 && (
            <div className="mt-4">
              <div className="flex justify-between items-center mb-2">
                <h3 className="text-sm font-medium text-gray-700">Uploaded Files</h3>
                <button 
                  onClick={clearUploads}
                  className="text-xs text-red-500 hover:text-red-700"
                >
                  Clear All
                </button>
              </div>
              
              <div className="space-y-2">
                {uploadedFiles.map((file) => (
                  <div 
                    key={file.id} 
                    className={`p-3 rounded-lg border ${
                      file.status === 'success' 
                        ? 'border-green-200 bg-green-50' 
                        : file.status === 'error'
                        ? 'border-red-200 bg-red-50'
                        : 'border-gray-200 bg-gray-50'
                    }`}
                  >
                    <div className="flex items-start">
                      <DocumentTextIcon 
                        className={`h-5 w-5 flex-shrink-0 ${
                          file.status === 'success' 
                            ? 'text-green-500' 
                            : file.status === 'error'
                            ? 'text-red-500'
                            : 'text-gray-400'
                        }`} 
                      />
                      <div className="ml-3 flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">{file.name}</p>
                        <div className="flex justify-between items-center mt-1">
                          <p className="text-xs text-gray-500">
                            {formatFileSize(file.size)}
                          </p>
                          {file.status === 'uploading' && (
                            <span className="inline-flex items-center text-xs text-blue-600">
                              <ArrowPathIcon className="h-3 w-3 mr-1 animate-spin" />
                              Uploading...
                            </span>
                          )}
                          {file.status === 'success' && (
                            <span className="text-xs text-green-600">✓ Indexed</span>
                          )}
                          {file.status === 'error' && (
                            <span className="text-xs text-red-600">Error</span>
                          )}
                        </div>
                        {file.status === 'error' && file.error && (
                          <p className="text-xs text-red-500 mt-1 truncate">
                            {file.error}
                          </p>
                        )}
                      </div>
                      {file.status !== 'uploading' && (
                        <button 
                          onClick={(e) => {
                            e.stopPropagation();
                            setUploadedFiles(prev => prev.filter(f => f.id !== file.id));
                          }}
                          className="text-gray-400 hover:text-gray-600"
                        >
                          <XCircleIcon className="h-5 w-5" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
        
        <div className="p-4 border-t border-gray-200">
          <div className="flex items-center justify-between text-sm">
            <div>
              <p className="font-medium">Documents Indexed</p>
              <p className="text-2xl font-bold text-blue-600">{uploadedFiles.filter(f => f.status === 'success').length}</p>
            </div>
            <div className="text-right">
              <p className="font-medium">Total Size</p>
              <p className="text-gray-700">
                {formatFileSize(uploadedFiles.reduce((sum, file) => sum + file.size, 0))}
              </p>
            </div>
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white shadow-sm z-10">
          <div className="flex items-center h-16 px-4 sm:px-6 lg:px-8">
            <button 
              onClick={toggleSidebar}
              className="mr-4 text-gray-500 hover:text-gray-700 lg:hidden"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <h1 className="text-xl font-semibold text-gray-900">RAG Assistant</h1>
          </div>
        </header>
        
        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
          <div className="max-w-4xl mx-auto space-y-6">
            {messages.map((message, index) => (
              <div 
                key={message.id || index}
                className={`flex ${
                  message.sender === 'user' ? 'justify-end' : 'justify-start'
                }`}
              >
                <div 
                  className={`max-w-3xl rounded-lg px-4 py-3 ${
                    message.sender === 'user' 
                      ? 'bg-blue-600 text-white' 
                      : message.sender === 'error'
                      ? 'bg-red-100 text-red-800'
                      : message.sender === 'bot'
                      ? 'bg-blue-50 text-gray-900'
                      : 'bg-white border border-gray-200'
                  } shadow-sm`}
                >
                  {message.sender === 'bot' ? (
                    <div className="space-y-4">
                      <div className="prose max-w-none">
                        <ReactMarkdown
                          components={{
                            code({node, inline, className, children, ...props}) {
                              const match = /language-(\w+)/.exec(className || '');
                              return !inline && match ? (
                                <SyntaxHighlighter
                                  style={vscDarkPlus}
                                  language={match[1]}
                                  PreTag="div"
                                  {...props}
                                >
                                  {String(children).replace(/\n$/, '')}
                                </SyntaxHighlighter>
                              ) : (
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              );
                            },
                          }}
                        >
                          {message.text}
                        </ReactMarkdown>
                      </div>
                      {message.contexts && message.contexts.length > 0 && (
                        <div className="mt-4 border-t border-gray-200 pt-3">
                          <p className="text-sm font-medium text-gray-700 mb-2">Sources:</p>
                          <div className="space-y-2">
                            {message.contexts.map((ctx, idx) => (
                              <div key={idx} className="bg-gray-50 p-3 rounded-md border border-gray-100">
                                <p className="text-sm text-gray-800">{ctx.text}</p>
                                {ctx.source && (
                                  <p className="text-xs text-gray-500 mt-1">
                                    <span className="font-medium">Source:</span> {ctx.source}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap">{message.text}</div>
                  )}
                  
                  {/* Context sources are now shown in the bot message section */}
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="flex justify-start">
                <div className="bg-white rounded-lg px-4 py-3 border border-gray-200 shadow-sm">
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>
        
        {/* Input Area */}
        <div className="bg-white border-t border-gray-200 p-4">
          <div className="max-w-4xl mx-auto">
            {/* Model status indicator */}
            <div className="mb-2">
              {modelStatus === MODEL_STATUS.LOADING && (
                <div className="flex items-center text-yellow-600">
                  <Cog6ToothIcon className="h-4 w-4 mr-1 animate-spin" />
                  <span>Initializing local model...</span>
                </div>
              )}
              {modelStatus === MODEL_STATUS.READY && (
                <div className="flex items-center text-green-600">
                  <CheckCircleIcon className="h-4 w-4 mr-1" />
                  <span>Mistral model ready</span>
                </div>
              )}
              {modelStatus === MODEL_STATUS.ERROR && (
                <div className="flex items-center text-red-600">
                  <ExclamationCircleIcon className="h-4 w-4 mr-1" />
                  <span>{modelError || 'Model error'}</span>
                </div>
              )}
            </div>
            
            {/* Input form */}
            <form onSubmit={handleSubmit} className="flex space-x-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={
                  modelStatus === MODEL_STATUS.READY 
                    ? "Ask a question about your documents..."
                    : "Initializing model, please wait..."
                }
                className="flex-1 p-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                disabled={isLoading || modelStatus !== MODEL_STATUS.READY}
              />
              <button
                type="submit"
                disabled={isLoading || !query.trim() || modelStatus !== MODEL_STATUS.READY}
                className={`p-2 rounded-lg ${
                  isLoading || !query.trim() || modelStatus !== MODEL_STATUS.READY
                    ? 'bg-gray-200 text-gray-500 cursor-not-allowed'
                    : 'bg-blue-500 text-white hover:bg-blue-600'
                }`}
                title={modelStatus !== MODEL_STATUS.READY ? 'Model is not ready' : 'Send message'}
              >
                {isLoading ? (
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                ) : (
                  <PaperAirplaneIcon className="h-5 w-5" />
                )}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
