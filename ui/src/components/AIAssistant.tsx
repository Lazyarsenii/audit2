'use client';

import { useState, useRef, useEffect } from 'react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface AIAssistantProps {
  onToggle?: (isOpen: boolean) => void;
}

const SUGGESTED_QUESTIONS = [
  'How is the repository health score calculated?',
  'What does technical debt score mean?',
  'How to improve my project readiness?',
  'Explain cost estimation methodology',
  'What contract requirements should I check?',
];

// Simple AI responses based on keywords (can be replaced with real AI API)
function getAIResponse(question: string): string {
  const q = question.toLowerCase();

  if (q.includes('health') || q.includes('repo health')) {
    return `**Repository Health Score (0-12 points)** measures operational readiness:

• **Documentation (0-3)**: README quality, API docs, inline comments
• **Structure (0-3)**: Project organization, naming conventions, config files
• **Runability (0-3)**: Build scripts, Docker, CI/CD setup
• **Commit History (0-3)**: Commit quality, frequency, messages

A score of 6+ is considered acceptable for most projects. Enterprise projects typically require 9+.`;
  }

  if (q.includes('tech') && q.includes('debt')) {
    return `**Technical Debt Score (0-15 points)** - higher is better (less debt):

• **Architecture (0-3)**: Modularity, separation of concerns
• **Code Quality (0-3)**: Complexity, duplication, style consistency
• **Testing (0-3)**: Test coverage, test quality
• **Infrastructure (0-3)**: Deployment, monitoring, logging
• **Security (0-3)**: Vulnerabilities, dependency security

Score interpretation:
- 12-15: Excellent, minimal debt
- 8-11: Good, manageable debt
- 4-7: Needs improvement
- 0-3: Critical technical debt`;
  }

  if (q.includes('readiness') || q.includes('ready')) {
    return `**Project Readiness Assessment** evaluates if a project is ready for formal evaluation:

**Levels:**
- **Not Ready (<40%)**: Significant work needed
- **Needs Work (40-60%)**: Several issues to address
- **Almost Ready (60-80%)**: Minor improvements needed
- **Ready (80-95%)**: All major criteria met
- **Exemplary (95%+)**: Exceeds expectations

**Key Checks:**
1. Documentation completeness
2. Dependency declarations
3. Docker/containerization
4. Test coverage
5. CI/CD pipeline
6. Security scan results

To improve readiness, address the blockers first, then critical issues.`;
  }

  if (q.includes('cost') || q.includes('estimat') || q.includes('price')) {
    return `**Cost Estimation Methodology**:

**Forward-Looking Estimate** (based on complexity):
- Analysis phase: 5-15% of total
- Design phase: 10-20%
- Development: 40-50%
- QA/Testing: 15-25%
- Documentation: 5-10%

**Historical Estimate** (based on commit history):
- Analyzes active development days
- Calculates person-months from commit patterns
- Applies regional hourly rates

**Regional Rates:**
- EU Standard: €35-85/hour
- Ukraine R&D: $15-50/hour
- US Standard: $50-130/hour

**Tech Debt Multiplier**: Adds 10-50% based on debt level.`;
  }

  if (q.includes('contract') || q.includes('compliance') || q.includes('requirement')) {
    return `**Contract Compliance Checking**:

We support checking against various contract profiles:

• **Global Fund R13**: Healthcare grants (HIPAA, ISO 22301, GDPR)
• **EU GDPR**: Data protection requirements
• **HIPAA Healthcare**: US healthcare standards
• **ISO 27001**: Information security
• **PCI DSS**: Payment card security

Each contract defines:
- Minimum scores for health metrics
- Required security checks
- Documentation requirements
- Blocking vs non-blocking requirements

To check compliance, go to **Workflow > Select Contract** or **Contracts > Compliance Check**.`;
  }

  if (q.includes('document') || q.includes('act') || q.includes('invoice')) {
    return `**Document Generation**:

Available documents:
• **Repository Review**: Full technical analysis report
• **Technical Summary**: Executive summary
• **Act of Work**: Formal work completion document
• **Invoice**: Payment request document
• **Partner Report**: Stakeholder summary

Languages: Ukrainian, English, Russian
Currencies: USD, EUR, UAH

Go to **Workflow > Documents** or **Documents** page to generate.`;
  }

  if (q.includes('profile') || q.includes('setting')) {
    return `**Evaluation Profiles** define pricing and requirements:

**Built-in Profiles:**
- EU Standard R&D (€35-85/hr)
- Ukraine R&D ($15-50/hr)
- EU Enterprise (€45-110/hr)
- US Standard ($50-130/hr)
- Startup/MVP ($25-70/hr)

**Customization:**
1. Go to **Settings > Profiles**
2. Or create custom profile in **Workflow > Add Custom**

Each profile includes:
- Hourly rates (Junior/Middle/Senior)
- Minimum requirements (Health, Debt, Readiness)
- Currency and region`;
  }

  // Default response
  return `I can help you with:

• **Repository Health**: How code quality is scored
• **Technical Debt**: Understanding debt metrics
• **Readiness Assessment**: Project evaluation preparation
• **Cost Estimation**: Pricing methodology
• **Contract Compliance**: Requirements checking
• **Document Generation**: Creating acts, invoices

What would you like to know more about?`;
}

export default function AIAssistant({ onToggle }: AIAssistantProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your Repo Auditor assistant. I can help you understand scoring, cost estimation, compliance requirements, and more. What would you like to know?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleToggle = (open: boolean) => {
    setIsOpen(open);
    onToggle?.(open);
  };

  const handleSend = async (text?: string) => {
    const messageText = text || input.trim();
    if (!messageText) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: messageText,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    // Simulate AI thinking
    await new Promise((resolve) => setTimeout(resolve, 500 + Math.random() * 1000));

    // Get AI response
    const response = getAIResponse(messageText);
    const assistantMessage: Message = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: response,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, assistantMessage]);
    setIsTyping(false);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      {/* Floating Button - only show when closed */}
      <button
        onClick={() => handleToggle(true)}
        className={`fixed bottom-6 right-6 w-14 h-14 bg-primary-600 hover:bg-primary-700 text-white rounded-full shadow-lg flex items-center justify-center transition-all z-40 ${
          isOpen ? 'scale-0 opacity-0' : 'scale-100 opacity-100'
        }`}
        title="AI Assistant"
      >
        <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
      </button>

      {/* Sidebar Chat - pushes content */}
      <div
        className={`fixed top-0 right-0 h-screen bg-white shadow-2xl border-l border-slate-200 z-50 flex flex-col transition-all duration-300 ease-in-out ${
          isOpen ? 'w-96 translate-x-0' : 'w-0 translate-x-full'
        }`}
      >
        {isOpen && (
          <>
            {/* Header */}
            <div className="bg-primary-600 text-white px-4 py-3 flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                </div>
                <div>
                  <div className="font-semibold">AI Assistant</div>
                  <div className="text-xs text-primary-100">Ask anything about auditing</div>
                </div>
              </div>
              <button
                onClick={() => handleToggle(false)}
                className="p-1 hover:bg-white/20 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-2 ${
                      message.role === 'user'
                        ? 'bg-primary-600 text-white rounded-br-md'
                        : 'bg-white text-slate-700 border border-slate-200 rounded-bl-md shadow-sm'
                    }`}
                  >
                    <div
                      className="text-sm whitespace-pre-wrap"
                      dangerouslySetInnerHTML={{
                        __html: message.content
                          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                          .replace(/\n/g, '<br/>'),
                      }}
                    />
                  </div>
                </div>
              ))}
              {isTyping && (
                <div className="flex justify-start">
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Suggested Questions */}
            {messages.length <= 2 && (
              <div className="px-4 py-2 border-t border-slate-100 bg-white flex-shrink-0">
                <div className="text-xs text-slate-500 mb-2">Suggested questions:</div>
                <div className="flex flex-wrap gap-1">
                  {SUGGESTED_QUESTIONS.slice(0, 3).map((q) => (
                    <button
                      key={q}
                      onClick={() => handleSend(q)}
                      className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-600 px-2 py-1 rounded-full transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input */}
            <div className="p-3 border-t border-slate-200 bg-white flex-shrink-0">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your question..."
                  className="flex-1 px-4 py-2 border border-slate-200 rounded-full focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
                />
                <button
                  onClick={() => handleSend()}
                  disabled={!input.trim() || isTyping}
                  className="w-10 h-10 bg-primary-600 hover:bg-primary-700 text-white rounded-full flex items-center justify-center disabled:opacity-50 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  );
}
