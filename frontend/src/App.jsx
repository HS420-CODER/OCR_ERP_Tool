import { useState } from 'react'
import axios from 'axios'
import './App.css'

// Use relative path - Vite proxy handles routing to backend in development
// In production, the Flask backend serves the frontend from /api/* routes
const API_URL = '/api'

function App() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [language, setLanguage] = useState('ar')  // Default to Arabic
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [structuredResult, setStructuredResult] = useState(null)
  const [error, setError] = useState(null)
  const [viewMode, setViewMode] = useState('structured')  // Default to structured view

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      setResult(null)
      setError(null)

      if (selectedFile.type.startsWith('image/')) {
        const reader = new FileReader()
        reader.onloadend = () => {
          setPreview(reader.result)
        }
        reader.readAsDataURL(selectedFile)
      } else {
        setPreview(null)
      }
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      setFile(droppedFile)
      setResult(null)
      setError(null)

      if (droppedFile.type.startsWith('image/')) {
        const reader = new FileReader()
        reader.onloadend = () => {
          setPreview(reader.result)
        }
        reader.readAsDataURL(droppedFile)
      } else {
        setPreview(null)
      }
    }
  }

  const handleDragOver = (e) => {
    e.preventDefault()
  }

  const processOCR = async () => {
    if (!file) {
      setError('Please select a file first')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)
    setStructuredResult(null)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('lang', language)
    formData.append('structured', 'true')  // Get structured output in single request

    try {
      // Single request with structured=true to avoid concurrent OCR conflicts
      const ocrResponse = await axios.post(`${API_URL}/ocr`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      if (ocrResponse.data.success) {
        const data = ocrResponse.data.data
        setResult(data)

        // Extract structured output from the response if available
        if (data.structured_output) {
          setStructuredResult({
            document_type: data.metadata?.document_type || 'DOCUMENT',
            is_bilingual: data.metadata?.is_bilingual || false,
            formatted_output: data.structured_output,
            raw_text: data.full_text,
            language: data.language,
            fields: data.metadata?.fields || null,
            sections: data.metadata?.sections || null
          })
        }
      } else {
        setError(ocrResponse.data.error || 'OCR processing failed')
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to process file')
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = () => {
    if (result) {
      const text = result.pages.map(p => p.full_text).join('\n\n--- Page Break ---\n\n')
      navigator.clipboard.writeText(text)
      alert('Text copied to clipboard!')
    }
  }

  const downloadJSON = () => {
    if (result) {
      const dataStr = JSON.stringify(result, null, 2)
      const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr)
      const exportFileDefaultName = 'ocr_result.json'

      const linkElement = document.createElement('a')
      linkElement.setAttribute('href', dataUri)
      linkElement.setAttribute('download', exportFileDefaultName)
      linkElement.click()
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>OCR Tool for ERP</h1>
        <p>Extract text from images and PDFs using PaddleOCR</p>
      </header>

      <main className="main">
        <div className="upload-section">
          <div
            className={`dropzone ${file ? 'has-file' : ''}`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
          >
            {preview ? (
              <img src={preview} alt="Preview" className="preview-image" />
            ) : file ? (
              <div className="file-info">
                <span className="file-icon">📄</span>
                <span className="file-name">{file.name}</span>
              </div>
            ) : (
              <div className="dropzone-content">
                <span className="upload-icon">📁</span>
                <p>Drag & drop a file here</p>
                <p className="or">or</p>
                <label className="file-input-label">
                  Browse Files
                  <input
                    type="file"
                    accept=".png,.jpg,.jpeg,.gif,.bmp,.tiff,.pdf"
                    onChange={handleFileChange}
                    className="file-input"
                  />
                </label>
              </div>
            )}
          </div>

          {file && (
            <button className="change-file-btn" onClick={() => {
              setFile(null)
              setPreview(null)
              setResult(null)
            }}>
              Change File
            </button>
          )}

          <div className="options">
            <div className="option-group">
              <label>Language:</label>
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="en">English</option>
                <option value="ar">Arabic (العربية)</option>
              </select>
            </div>
          </div>

          <button
            className={`process-btn ${loading ? 'loading' : ''}`}
            onClick={processOCR}
            disabled={!file || loading}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Processing...
              </>
            ) : (
              'Extract Text'
            )}
          </button>

          {error && (
            <div className="error-message">
              <span>⚠️</span> {error}
            </div>
          )}
        </div>

        {result && (
          <div className="result-section">
            <div className="result-header">
              <h2>OCR Results</h2>
              <div className="result-actions">
                <div className="view-toggle">
                  {structuredResult && (
                    <button
                      className={viewMode === 'structured' ? 'active' : ''}
                      onClick={() => setViewMode('structured')}
                    >
                      Structured View
                    </button>
                  )}
                  <button
                    className={viewMode === 'text' ? 'active' : ''}
                    onClick={() => setViewMode('text')}
                  >
                    Text View
                  </button>
                  <button
                    className={viewMode === 'detailed' ? 'active' : ''}
                    onClick={() => setViewMode('detailed')}
                  >
                    Detailed View
                  </button>
                </div>
                <button className="action-btn" onClick={copyToClipboard}>
                  📋 Copy
                </button>
                <button className="action-btn" onClick={downloadJSON}>
                  💾 Download JSON
                </button>
              </div>
            </div>

            <div className="result-stats">
              <span>Type: {result.type?.toUpperCase() || 'UNKNOWN'}</span>
              {result.total_pages && <span>Pages: {result.processed_pages}/{result.total_pages}</span>}
              <span>
                Text Blocks: {result.pages.reduce((sum, p) => sum + p.text_blocks.length, 0)}
              </span>
            </div>

            {viewMode === 'structured' && structuredResult ? (
              <div className="result-structured">
                {/* Document Type Badge */}
                <div className="document-type-badge">
                  <span className="badge">{structuredResult.document_type?.toUpperCase() || 'DOCUMENT'}</span>
                  {structuredResult.is_bilingual && <span className="badge bilingual">Bilingual</span>}
                  {structuredResult.language && (
                    <span className="badge language">{structuredResult.language === 'ar' ? 'Arabic' : 'English'}</span>
                  )}
                </div>

                {/* Formatted Output - Primary display */}
                {structuredResult.formatted_output && (
                  <div className="formatted-output">
                    <h3>Structured Output</h3>
                    <pre className="formatted-text">{structuredResult.formatted_output}</pre>
                  </div>
                )}

                {/* Key-Value Pairs Table (if available) */}
                {structuredResult.fields && Object.keys(structuredResult.fields).length > 0 && (
                  <div className="fields-section">
                    <h3>Extracted Fields ({Object.keys(structuredResult.fields).length})</h3>
                    <table className="fields-table">
                      <thead>
                        <tr>
                          <th>Field (Arabic)</th>
                          <th>Field (English)</th>
                          <th>Value</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(structuredResult.fields).map(([key, value], idx) => (
                          <tr key={idx}>
                            <td className="arabic-cell" dir="rtl">{key}</td>
                            <td className="english-cell">{value.english_key || '-'}</td>
                            <td className="value-cell">{value.value || value}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Document Sections (if available) */}
                {structuredResult.sections && structuredResult.sections.length > 0 && (
                  <div className="sections-container">
                    <h3>Document Sections</h3>
                    {structuredResult.sections.map((section, idx) => (
                      <div key={idx} className="document-section">
                        <h4 className="section-title">{section.name}</h4>
                        <div className="section-content" dir={section.is_rtl ? 'rtl' : 'ltr'}>
                          {section.content}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : viewMode === 'text' ? (
              <div className="result-text">
                {result.pages.map((page, idx) => (
                  <div key={idx} className="page-result">
                    {result.pages.length > 1 && (
                      <h3 className="page-header">Page {page.page_number || idx + 1}</h3>
                    )}
                    <pre className="extracted-text">{page.full_text || '(No text detected)'}</pre>
                  </div>
                ))}
              </div>
            ) : (
              <div className="result-detailed">
                {result.pages.map((page, pageIdx) => (
                  <div key={pageIdx} className="page-detailed">
                    {result.pages.length > 1 && (
                      <h3 className="page-header">Page {page.page_number || pageIdx + 1}</h3>
                    )}
                    <table className="text-blocks-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Text</th>
                          <th>Confidence</th>
                        </tr>
                      </thead>
                      <tbody>
                        {page.text_blocks.map((block, blockIdx) => (
                          <tr key={blockIdx}>
                            <td>{blockIdx + 1}</td>
                            <td className="text-cell">{block.text}</td>
                            <td className="confidence-cell">
                              <span className={`confidence ${block.confidence >= 0.95 ? 'high' : block.confidence >= 0.8 ? 'medium' : 'low'}`}>
                                {(block.confidence * 100).toFixed(1)}%
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="footer">
        <p>Powered by PaddleOCR | Supports English & Arabic</p>
      </footer>
    </div>
  )
}

export default App
