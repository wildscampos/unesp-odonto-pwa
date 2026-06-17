import {
  BookOpen,
  CalendarDays,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ClipboardCheck,
  Home,
  RotateCcw,
  Signal,
  XCircle
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

type Letter = "A" | "B" | "C" | "D" | "E";

type Question = {
  id: string;
  subject: string;
  topic: string;
  prompt: string;
  options: Record<Letter, string>;
  answer: Letter;
  explanation: string;
  source_notes?: string;
  validation_notes?: string;
};

type Exam = {
  id: string;
  date: string;
  title: string;
  questionCount: number;
  questions: Question[];
};

type ExamPayload = {
  generatedAt: string;
  schedule: {
    first_exam_date: string;
    exam_weekdays: number[];
    answers_in_app: boolean;
  };
  exams: Exam[];
};

type Attempt = {
  examId: string;
  answers: Record<string, Letter>;
  finishedAt?: string;
};

type Tab = "home" | "exam" | "review" | "history";

const LETTERS: Letter[] = ["A", "B", "C", "D", "E"];
const STORAGE_KEY = "unesp-odonto-attempts-v1";

export function App() {
  const [payload, setPayload] = useState<ExamPayload | null>(null);
  const [attempts, setAttempts] = useState<Record<string, Attempt>>({});
  const [selectedExamId, setSelectedExamId] = useState<string>("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [tab, setTab] = useState<Tab>("home");
  const [isOffline, setIsOffline] = useState(!navigator.onLine);

  useEffect(() => {
    loadExams().then((data) => {
      setPayload(data);
      setSelectedExamId(data.exams[data.exams.length - 1]?.id ?? "");
    });

    const saved = window.localStorage.getItem(STORAGE_KEY);
    if (saved) setAttempts(JSON.parse(saved));

    const onOnline = () => setIsOffline(false);
    const onOffline = () => setIsOffline(true);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(attempts));
  }, [attempts]);

  const exams = payload?.exams ?? [];
  const selectedExam = exams.find((exam) => exam.id === selectedExamId) ?? exams[exams.length - 1];
  const attempt = selectedExam ? attempts[selectedExam.id] ?? createAttempt(selectedExam.id) : undefined;
  const result = selectedExam && attempt?.finishedAt ? calculateResult(selectedExam, attempt) : null;

  const nextExamText = useMemo(() => {
    if (!payload) return "Carregando agenda";
    return `Novas provas: segunda, quarta e sexta`;
  }, [payload]);

  function setAnswer(questionId: string, letter: Letter) {
    if (!selectedExam) return;
    setAttempts((current) => {
      const active = current[selectedExam.id] ?? createAttempt(selectedExam.id);
      return {
        ...current,
        [selectedExam.id]: {
          ...active,
          answers: { ...active.answers, [questionId]: letter }
        }
      };
    });
  }

  function finishExam() {
    if (!selectedExam) return;
    setAttempts((current) => {
      const active = current[selectedExam.id] ?? createAttempt(selectedExam.id);
      return {
        ...current,
        [selectedExam.id]: { ...active, finishedAt: new Date().toISOString() }
      };
    });
    setTab("review");
  }

  function resetExam() {
    if (!selectedExam) return;
    setAttempts((current) => {
      const next = { ...current };
      delete next[selectedExam.id];
      return next;
    });
    setCurrentIndex(0);
    setTab("exam");
  }

  if (!payload || !selectedExam || !attempt) {
    return (
      <main className="app loading">
        <BookOpen size={32} />
        <p>Carregando simulados...</p>
      </main>
    );
  }

  const answeredCount = Object.keys(attempt.answers).length;
  const currentQuestion = selectedExam.questions[currentIndex];
  const canFinish = answeredCount === selectedExam.questions.length;
  const isLastQuestion = currentIndex === selectedExam.questions.length - 1;
  const hasAnsweredCurrentQuestion = Boolean(attempt.answers[currentQuestion.id]);
  const showFinishButton = isLastQuestion && hasAnsweredCurrentQuestion;

  return (
    <main className="app">
      <header className="topbar">
        <div className="brand-lockup">
          <img className="brand-mark" src={`${import.meta.env.BASE_URL}icons/icon-192-v2.png`} alt="" />
          <div>
            <h1>Simulados UNESP</h1>
            <p>{nextExamText}</p>
          </div>
        </div>
        <div className={isOffline ? "net offline" : "net online"} title={isOffline ? "Offline" : "Online"}>
          <Signal size={18} />
        </div>
      </header>

      {tab === "home" && (
        <section className="screen">
          <div className="status-panel">
            <div>
              <span className="date-label">{formatDate(selectedExam.date)}</span>
              <h2>{selectedExam.title}</h2>
            </div>
            <div className="score-ring">
              <strong>{attempt.finishedAt && result ? `${result.score}` : answeredCount}</strong>
              <span>{attempt.finishedAt ? "acertos" : "feitas"}</span>
            </div>
          </div>

          <div className="progress-block">
            <div className="progress-row">
              <span>Progresso</span>
              <strong>{answeredCount}/{selectedExam.questions.length}</strong>
            </div>
            <div className="progress-track">
              <div style={{ width: `${(answeredCount / selectedExam.questions.length) * 100}%` }} />
            </div>
          </div>

          <button className="primary-action" onClick={() => setTab(attempt.finishedAt ? "review" : "exam")}>
            {attempt.finishedAt ? "Ver correção" : answeredCount ? "Continuar prova" : "Iniciar prova"}
          </button>

          <section className="subject-grid" aria-label="Resumo por matéria">
            {subjectSummary(selectedExam, attempt).map((item) => (
              <article className="subject-card" key={item.subject}>
                <span>{item.subject}</span>
                <strong>{item.done}/{item.total}</strong>
              </article>
            ))}
          </section>
        </section>
      )}

      {tab === "exam" && (
        <section className="screen exam-screen">
          <div className="question-tools">
            <button className="icon-button" onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))} aria-label="Questão anterior">
              <ChevronLeft size={22} />
            </button>
            <div>
              <span>Questão {currentIndex + 1} de {selectedExam.questions.length}</span>
              <strong>{currentQuestion.subject} · {currentQuestion.topic}</strong>
            </div>
            <button className="icon-button" onClick={() => setCurrentIndex(Math.min(selectedExam.questions.length - 1, currentIndex + 1))} aria-label="Próxima questão">
              <ChevronRight size={22} />
            </button>
          </div>

          <article className="question-card">
            <p>{currentQuestion.prompt}</p>
            <div className="options">
              {LETTERS.map((letter) => (
                <button
                  className={attempt.answers[currentQuestion.id] === letter ? "option selected" : "option"}
                  key={letter}
                  onClick={() => setAnswer(currentQuestion.id, letter)}
                >
                  <span>{letter}</span>
                  {currentQuestion.options[letter]}
                </button>
              ))}
            </div>
          </article>

          <div className="exam-actions">
            <button className="secondary-action" onClick={() => setTab("home")}>Salvar e continuar depois</button>
            {showFinishButton && (
              <button className="primary-action compact" onClick={finishExam} disabled={!canFinish}>
                Finalizar
              </button>
            )}
          </div>
        </section>
      )}

      {tab === "review" && (
        <section className="screen review-screen">
          {result ? (
            <>
              <div className="result-panel">
                <ClipboardCheck size={26} />
                <div>
                  <h2>{result.score}/{result.total} acertos</h2>
                  <p>{Math.round((result.score / result.total) * 100)}% de aproveitamento</p>
                </div>
              </div>

              <div className="review-list">
                {selectedExam.questions.map((question, index) => {
                  const marked = attempt.answers[question.id];
                  const isCorrect = marked === question.answer;
                  return (
                    <article className={isCorrect ? "review-item correct" : "review-item wrong"} key={question.id}>
                      <div className="review-head">
                        {isCorrect ? <CheckCircle2 size={20} /> : <XCircle size={20} />}
                        <strong>{index + 1}. {question.subject}</strong>
                      </div>
                      <p>{question.prompt}</p>
                      <div className="answer-line">
                        <span>Sua resposta: {marked ?? "-"}</span>
                        <span>Correta: {question.answer}</span>
                      </div>
                      {!isCorrect && <p className="explanation">{question.explanation}</p>}
                    </article>
                  );
                })}
              </div>

              <button className="secondary-action full" onClick={resetExam}>
                <RotateCcw size={18} />
                Refazer prova
              </button>
            </>
          ) : (
            <div className="empty-state">
              <ClipboardCheck size={28} />
              <p>Finalize a prova para liberar a correção.</p>
            </div>
          )}
        </section>
      )}

      {tab === "history" && (
        <section className="screen">
          <h2 className="section-title">Histórico</h2>
          <div className="history-list">
            {[...exams].reverse().map((exam) => {
              const itemAttempt = attempts[exam.id];
              const itemResult = itemAttempt?.finishedAt ? calculateResult(exam, itemAttempt) : null;
              return (
                <button className="history-row" key={exam.id} onClick={() => { setSelectedExamId(exam.id); setTab("home"); }}>
                  <CalendarDays size={20} />
                  <span>{formatDate(exam.date)}</span>
                  <strong>{itemResult ? `${itemResult.score}/${itemResult.total}` : "pendente"}</strong>
                </button>
              );
            })}
          </div>
        </section>
      )}

      <nav className="bottom-nav" aria-label="Navegação principal">
        <button className={tab === "home" ? "active" : ""} onClick={() => setTab("home")}>
          <Home size={21} />
          Início
        </button>
        <button className={tab === "exam" ? "active" : ""} onClick={() => setTab("exam")}>
          <BookOpen size={21} />
          Prova
        </button>
        <button className={tab === "review" ? "active" : ""} onClick={() => setTab("review")}>
          <ClipboardCheck size={21} />
          Correção
        </button>
        <button className={tab === "history" ? "active" : ""} onClick={() => setTab("history")}>
          <CalendarDays size={21} />
          Histórico
        </button>
      </nav>
    </main>
  );
}

async function loadExams(): Promise<ExamPayload> {
  const response = await fetch(`${import.meta.env.BASE_URL}data/exams.json?ts=${Date.now()}`, { cache: "no-store" });
  if (!response.ok) throw new Error("Falha ao carregar provas");
  return response.json();
}

function createAttempt(examId: string): Attempt {
  return { examId, answers: {} };
}

function calculateResult(exam: Exam, attempt: Attempt) {
  const score = exam.questions.reduce((sum, question) => sum + (attempt.answers[question.id] === question.answer ? 1 : 0), 0);
  return { score, total: exam.questions.length };
}

function subjectSummary(exam: Exam, attempt: Attempt) {
  const map = new Map<string, { subject: string; total: number; done: number }>();
  for (const question of exam.questions) {
    const item = map.get(question.subject) ?? { subject: question.subject, total: 0, done: 0 };
    item.total += 1;
    if (attempt.answers[question.id]) item.done += 1;
    map.set(question.subject, item);
  }
  return Array.from(map.values());
}

function formatDate(value: string) {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}
