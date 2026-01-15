import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { BookOpen, BrainCircuit, Camera, Send, CheckCircle, XCircle, Upload, Loader } from 'lucide-react';
import './App.css'; 

const API_URL = "http://127.0.0.1:5000";

function App() {
  const [activeTab, setActiveTab] = useState('tutor');

  return (
    <div className="app-container">
      {/* HEADER */}
      <header>
        <h1>Digital Dean 🎓</h1>
        <div className="subtitle">Nocturnal Focus Mode • Supabase Connected</div>
      </header>

      {/* NAVIGATION TABS */}
      <div className="tabs">
        <TabButton active={activeTab === 'tutor'} onClick={() => setActiveTab('tutor')} icon={<BookOpen size={20} />} label="Tutor" />
        <TabButton active={activeTab === 'quiz'} onClick={() => setActiveTab('quiz')} icon={<BrainCircuit size={20} />} label="Examiner" />
        <TabButton active={activeTab === 'grade'} onClick={() => setActiveTab('grade')} icon={<Camera size={20} />} label="Grader" />
      </div>

      {/* SURFACE CARD - PERSISTENCE FIX APPLIED */}
      <div className="main-card">
        {/* We use 'display: contents' so the layout behaves exactly as before, 
            but the component stays mounted in memory even when hidden. */}
        <div style={{ display: activeTab === 'tutor' ? 'contents' : 'none' }}>
          <TutorModule />
        </div>
        
        <div style={{ display: activeTab === 'quiz' ? 'contents' : 'none' }}>
          <QuizModule />
        </div>
        
        <div style={{ display: activeTab === 'grade' ? 'contents' : 'none' }}>
          <GraderModule />
        </div>
      </div>
    </div>
  );
}

// --- SUB-COMPONENTS ---

function TabButton({ active, onClick, icon, label }) {
  return (
    <button className={`tab-btn ${active ? 'active' : ''}`} onClick={onClick}>
      {icon} {label}
    </button>
  );
}

// 1. TUTOR MODULE
function TutorModule() {
  const [input, setInput] = useState('');
  const [chat, setChat] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false); // State for file upload
  const endRef = useRef(null);
  const fileInputRef = useRef(null); // Reference to hidden file input

  const sendMessage = async () => {
    if (!input.trim()) return;
    const userMsg = { role: 'user', text: input };
    setChat([...chat, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await axios.post(`${API_URL}/chat`, { question: input });
      setChat(prev => [...prev, { role: 'ai', text: res.data.reply }]);
    } catch (err) {
      setChat(prev => [...prev, { role: 'ai', text: "Error connecting to Digital Dean." }]);
    }
    setLoading(false);
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    // Add a system message so the user knows something is happening
    setChat(prev => [...prev, { role: 'ai', text: `📥 Analyzing ${file.name}... This may take a moment.` }]);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axios.post(`${API_URL}/upload`, formData);
      setChat(prev => [...prev, { role: 'ai', text: `✅ ${res.data.message} Ready for questions!` }]);
    } catch (err) {
      setChat(prev => [...prev, { role: 'ai', text: "❌ Upload failed. Check server logs." }]);
    }
    setUploading(false);
  };

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [chat]);

  const formatMessage = (text) => {
    let cleanText = text.replace(/\n\n+/g, '\n').trim(); 
    const parts = cleanText.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={index} style={{ color: '#fff', fontWeight: 'bold' }}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  return (
    <div>
      <div className="chat-window">
        {chat.length === 0 && (
          <div style={{ textAlign: 'center', marginTop: '100px', opacity: 0.5 }}>
            <BookOpen size={50} style={{ marginBottom: '20px', color: 'var(--primary)' }} />
            <p>Ready to analyze syllabus...</p>
          </div>
        )}
        {chat.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {formatMessage(msg.text)}
          </div>
        ))}
        {loading && <div className="message ai"><Loader className="spin" size={16}/> Thinking...</div>}
        <div ref={endRef} />
      </div>
      
      {/* INPUT AREA */}
      <div className="input-area">
        {/* Hidden File Input */}
        <input 
          type="file" 
          ref={fileInputRef} 
          style={{ display: 'none' }} 
          accept=".pdf" 
          onChange={handleFileUpload} 
        />
        
        {/* Upload Button */}
        <button 
          className="send-btn" 
          style={{ background: uploading ? '#334155' : 'var(--bg-layer)', border: '1px solid #334155' }}
          onClick={() => fileInputRef.current.click()}
          disabled={uploading}
        >
          {uploading ? <Loader className="spin" size={20} /> : <Upload size={20} color="var(--text-dim)" />}
        </button>

        <input 
          value={input} onChange={e => setInput(e.target.value)}
          onKeyPress={e => e.key === 'Enter' && sendMessage()}
          placeholder={uploading ? "Uploading syllabus..." : "Ask your syllabus anything..."}
          disabled={uploading}
        />
        <button className="send-btn" onClick={sendMessage} disabled={uploading}>
          <Send size={20} />
        </button>
      </div>
    </div>
  );
}

// 2. QUIZ MODULE
function QuizModule() {
  const [topic, setTopic] = useState('');
  const [quiz, setQuiz] = useState(null);
  const [loading, setLoading] = useState(false);
  const [answers, setAnswers] = useState({});
  const [showResults, setShowResults] = useState(false);
  const [score, setScore] = useState(0);

  const startQuiz = async () => {
    if (!topic) return;
    setLoading(true);
    setQuiz(null);
    setAnswers({});
    setShowResults(false);
    try {
      const res = await axios.post(`${API_URL}/quiz`, { topic });
      setQuiz(res.data.quiz);
    } catch (err) {
      alert("Failed to generate quiz. Try a broader topic.");
    }
    setLoading(false);
  };

  const handleOptionSelect = (qIndex, option) => {
    if (showResults) return;
    const letter = option.charAt(0);
    setAnswers(prev => ({ ...prev, [qIndex]: letter }));
  };

  const submitExam = () => {
    let newScore = 0;
    quiz.forEach((q, i) => {
      if (answers[i] === q.answer.charAt(0)) newScore++;
    });
    setScore(newScore);
    setShowResults(true);
  };

  return (
    <div className="quiz-container">
      {!quiz ? (
        <div style={{ textAlign: 'center', marginTop: '80px' }}>
          <BrainCircuit size={60} style={{ color: 'var(--teal-glow)', marginBottom: '20px' }} />
          <h3>Initialize Exam Protocol</h3>
          <div className="input-area" style={{ justifyContent: 'center' }}>
            <input 
              value={topic} onChange={e => setTopic(e.target.value)}
              placeholder="Enter Topic (e.g. Recursion)"
              style={{ maxWidth: '300px' }}
            />
            <button className="btn-primary" onClick={startQuiz} disabled={loading}>
              {loading ? "Generating..." : "Start Quiz"}
            </button>
          </div>
        </div>
      ) : (
        <div>
          {showResults && (
            <div className="grade-result" style={{ textAlign: 'center', marginBottom: '30px' }}>
              <h2 className="grade-score">{score} / 5</h2>
              <p style={{ color: 'var(--text-dim)' }}>{score >= 3 ? "PROTOCOL PASSED" : "REMEDIAL REQUIRED"}</p>
            </div>
          )}

          {quiz.map((q, i) => (
            <div key={i} style={{ marginBottom: '40px' }}>
              <p style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '15px' }}>
                <span style={{ color: 'var(--primary)', marginRight: '10px' }}>0{i+1}</span> 
                {q.question}
              </p>
              <div>
                {q.options.map((opt, idx) => {
                  const letter = opt.charAt(0);
                  const isSelected = answers[i] === letter;
                  const isCorrect = q.answer.startsWith(letter);
                  
                  let statusClass = '';
                  if (isSelected) statusClass = 'selected';
                  if (showResults) {
                    if (isCorrect) statusClass = 'correct';
                    else if (isSelected && !isCorrect) statusClass = 'wrong';
                  }

                  return (
                    <div 
                      key={idx} 
                      className={`quiz-option ${statusClass}`}
                      onClick={() => handleOptionSelect(i, opt)}
                    >
                      {showResults && isCorrect && <CheckCircle size={18} />}
                      {showResults && isSelected && !isCorrect && <XCircle size={18} />}
                      {opt}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
          
          {!showResults ? (
            <button className="btn-primary" style={{ width: '100%' }} onClick={submitExam}>Submit Exam</button>
          ) : (
            <button className="btn-primary" style={{ width: '100%', background: 'var(--bg-void)', border: '1px solid var(--primary)' }} onClick={() => setQuiz(null)}>New Quiz</button>
          )}
        </div>
      )}
    </div>
  );
}

// 3. GRADER MODULE
function GraderModule() {
  const [topic, setTopic] = useState('');
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    if (!file || !topic) return alert("Please provide topic and image");
    setLoading(true);
    const formData = new FormData();
    formData.append('image', file);
    formData.append('topic', topic);

    try {
      const res = await axios.post(`${API_URL}/grade`, formData);
      setResult(res.data);
    } catch (err) {
      alert("Grading failed.");
    }
    setLoading(false);
  };

  // --- NEW: Helper to clean up the AI text ---
  const formatFeedback = (text) => {
    if (!text) return null;

    // 1. Remove the "####" Header markers (replace with nothing to clean it up)
    let cleanText = text.replace(/#{1,6}\s/g, ''); 

    // 2. Split by bold markers (**)
    const parts = cleanText.split(/(\*\*.*?\*\*)/g);

    return parts.map((part, index) => {
      // If part starts/ends with **, make it Bold
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={index} style={{ color: '#fff', fontWeight: 'bold' }}>{part.slice(2, -2)}</strong>;
      }
      return part;
    });
  };

  return (
    <div>
      {!result ? (
        <div style={{ textAlign: 'center', marginTop: '50px' }}>
          <h3 style={{ color: 'var(--teal-glow)' }}>Handwriting Analysis</h3>
          
          <div style={{ maxWidth: '400px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <input 
              value={topic} onChange={e => setTopic(e.target.value)}
              placeholder="Topic (e.g. Ohm's Law)"
            />
            
            <div className="upload-zone" onClick={() => document.getElementById('fileInput').click()}>
              <Upload size={50} style={{ color: 'var(--text-dim)', marginBottom: '15px' }} />
              <p style={{ color: 'var(--text-dim)' }}>{file ? file.name : "Click to Upload Image"}</p>
              <input 
                id="fileInput" 
                type="file" 
                hidden 
                onChange={e => setFile(e.target.files[0])} 
                accept="image/*" 
              />
            </div>

            <button className="btn-primary" onClick={handleUpload} disabled={loading}>
              {loading ? "Scanning with Vision AI..." : "Grade Submission"}
            </button>
          </div>
        </div>
      ) : (
        <div className="grade-result">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', borderBottom: '1px solid #334155', paddingBottom: '20px' }}>
            <div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-dim)' }}>GRADED SCORE</div>
              <div className="grade-score">{result.score}</div>
            </div>
            <button className="btn-primary" style={{ background: 'transparent', border: '1px solid var(--text-dim)' }} onClick={() => setResult(null)}>Reset</button>
          </div>
          {/* USE THE NEW FORMATTER HERE */}
          <p style={{ lineHeight: '1.8', color: 'var(--text-mist)', whiteSpace: 'pre-wrap' }}>
            {formatFeedback(result.feedback)}
          </p>
        </div>
      )}
    </div>
  );
}

export default App;