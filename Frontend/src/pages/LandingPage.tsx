import React from "react";
import { motion } from "framer-motion";
import { useNavigate } from "react-router-dom";
import Snowfall from "react-snowfall";
import {
  ArrowRight,
  Cpu,
  Globe,
  Database,
  MessageSquare,
  ShieldCheck,
  UserCheck
} from "lucide-react";
import Footer from "../components/Layout/Footer";
import { useDemoAuth } from "../services/demoAuth";

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useDemoAuth();
  const handleDashboardClick = () => navigate(user ? "/dashboard/recovery" : "/login");

  const fadeIn = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.6 }
  };

  const steps = [
    {
      title: "Multilingual Recovery Voice",
      desc: "Sarvam, Whisper, and Groq power a respectful recovery conversation in the customer's preferred language.",
      icon: Cpu,
      color: "bg-[#d4a373]",
      textColor: "text-[#d4a373]"
    },
    {
      title: "Grounded Recovery Context",
      desc: "The existing RAG layer grounds approved invoice, policy, and dispute information during a recovery interaction.",
      icon: Database,
      color: "bg-[#d4a373]",
      textColor: "text-[#d4a373]"
    },
    {
      title: "Language-Aware Outreach",
      desc: "Voice and WhatsApp can use English, Hindi, Hinglish, and regional-language preferences.",
      icon: Globe,
      color: "bg-[#d4a373]",
      textColor: "text-[#d4a373]"
    },
    {
      title: "Explainable Revenue Risk",
      desc: "Field-derived overdue, value, contact-history, and promise signals produce a reasoned risk score.",
      icon: UserCheck,
      color: "bg-[#d4a373]",
      textColor: "text-[#d4a373]"
    },
    {
      title: "Bounded Escalation",
      desc: "Payment, opt-out, promise-to-pay, daily voice, and max-attempt stopping rules are enforced before escalation.",
      icon: ShieldCheck,
      color: "bg-[#d4a373]",
      textColor: "text-[#d4a373]"
    },
    {
      title: "Recovery WhatsApp Agent",
      desc: "Personalized reminders and secure payment links create a low-friction B2B recovery channel.",
      icon: MessageSquare,
      color: "bg-[#d4a373]",
      textColor: "text-[#d4a373]"
    },
  ];

  return (
    <div className="min-h-screen bg-[#fefae0] ambient-glow text-[#3d2b1f] selection:bg-[#d4a373]/20 overflow-x-hidden relative">
      {/* Grid Background */}
      <div
        className="fixed inset-0 z-0 opacity-15 pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(#d4a373 0.6px, transparent 0.6px)',
          backgroundSize: '32px 32px'
        }}
      />

      {/* Dynamic Golden Snowfall Background */}
      <Snowfall
        color="#d4a373"
        snowflakeCount={190}
        style={{
          position: "fixed",
          width: "100vw",
          height: "100vh",
          zIndex: 1,
          opacity: 0.85,
          pointerEvents: "none",
        }}
      />

      {/* Hero Section */}
      <section className="relative z-10 pt-32 pb-20 px-6 max-w-7xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#faedcd] border border-[#d4a373]/30 text-[#a87440] mb-8 shadow-sm"
        >
          <img src="/logo.png" className="w-5 h-5 object-contain" alt="" />
          <span className="text-xs font-bold uppercase tracking-wider">Track 03 · AI Revenue Recovery</span>
        </motion.div>

        <motion.h1
          className="text-6xl md:text-8xl font-black tracking-tight mb-8 bg-gradient-to-r from-[#3d2b1f] via-[#b5835a] to-[#d4a373] bg-clip-text text-transparent font-display leading-[1.1]"
          {...fadeIn}
        >
          Recover Revenue Before It Slips Away
        </motion.h1>

        <motion.p
          className="text-xl md:text-2xl text-[#3d2b1f]/80 max-w-3xl mx-auto mb-12 leading-relaxed font-sans"
          {...fadeIn}
          transition={{ delay: 0.2 }}
        >
          An AI agent that detects overdue B2B revenue, understands why payments are delayed, chooses the right intervention, and recovers money through multilingual voice and WhatsApp workflows.
        </motion.p>

        <motion.div
          className="flex flex-wrap justify-center gap-6"
          {...fadeIn}
          transition={{ delay: 0.4 }}
        >
          <button
            onClick={handleDashboardClick}
            className="group relative px-8 py-4 rounded-xl bg-[#d4a373] text-white hover:bg-[#c39162] transition-all duration-300 font-bold flex items-center gap-2 shadow-lg shadow-[#d4a373]/20 hover:shadow-[#d4a373]/30 active:scale-95 cursor-pointer"
          >
            View Recovery Dashboard
            <ArrowRight size={20} className="group-hover:translate-x-1 transition-transform" />
          </button>
          <div className="px-8 py-4 rounded-xl bg-[#faedcd] border border-[#d4a373]/20 text-[#3d2b1f] font-bold shadow-sm">Fictional demo data · No live API required</div>
        </motion.div>
      </section>

      {/* Stats/About Section */}
      <section className="relative z-10 py-20 px-6 max-w-7xl mx-auto border-t border-[#d4a373]/20">
        <div className="grid md:grid-cols-3 gap-12 text-center">
          <div className="space-y-2 bg-[#faedcd] rounded-xl p-6 border border-[#faedcd] shadow-sm hover:scale-[1.02] transition-transform relative z-10">
            <div className="text-5xl font-black text-[#d4a373] font-display">₹18.4L</div>
            <p className="text-[#3d2b1f]/80 font-bold">Fictional revenue-at-risk batch</p>
          </div>
          <div className="space-y-2 bg-[#faedcd] rounded-xl p-6 border border-[#faedcd] shadow-sm hover:scale-[1.02] transition-transform relative z-10">
            <div className="text-5xl font-black text-[#d4a373] font-display">3</div>
            <p className="text-[#3d2b1f]/80 font-bold">Maximum automated recovery attempts</p>
          </div>
          <div className="space-y-2 bg-[#faedcd] rounded-xl p-6 border border-[#faedcd] shadow-sm hover:scale-[1.02] transition-transform relative z-10">
            <div className="text-5xl font-black text-[#d4a373] font-display">1</div>
            <p className="text-[#3d2b1f]/80 font-bold">Active promise pauses outreach</p>
          </div>
        </div>
      </section>

      {/* Problem & Solution Section */}
      <section className="relative z-10 py-24 px-6 max-w-7xl mx-auto border-t border-[#d4a373]/20">
        <div className="grid md:grid-cols-2 gap-16 items-center">
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="space-y-8"
          >
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#faedcd] border border-[#d4a373]/30 text-[#a87440] shadow-sm relative z-10">
              <span className="text-xs font-bold uppercase tracking-wider">The Problem & Our Solution</span>
            </div>
            <h2 className="text-4xl md:text-6xl font-black text-[#3d2b1f] font-display leading-[1.1] relative z-10">
              Why We Built <br/>
              <span className="bg-gradient-to-r from-[#b5835a] to-[#d4a373] bg-clip-text text-transparent">Sambhaash AI</span>
            </h2>
            <div className="space-y-6 relative z-10">
              <p className="text-lg text-[#3d2b1f]/80 leading-relaxed font-sans">
                B2B receivables slip through when a generic reminder cannot reach the right decision-maker in a language they are comfortable using. Manual follow-up is costly, inconsistent, and difficult to audit.
              </p>
              <p className="text-lg text-[#3d2b1f]/80 leading-relaxed font-sans">
                Sambhaash AI detects revenue at risk, diagnoses a bounded payment cause, chooses an approved intervention, and records promises or payment confirmation. Sarvam voice, Whisper, Groq, RAG, Twilio, and WhatsApp remain reusable recovery channels—not the product outcome itself.
              </p>
            </div>
          </motion.div>
          
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            className="grid grid-cols-2 gap-6 relative z-10"
          >
            <div className="p-8 rounded-xl bg-[#faedcd] border border-[#faedcd] hover:border-[#d4a373]/50 hover:scale-[1.03] transition-all duration-300 group shadow-sm flex flex-col relative z-10 translate-y-8">
               <div className="absolute inset-0 bg-[#fefae0]/40 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none z-0" />
               <div className="w-12 h-12 rounded-xl bg-[#d4a373]/20 flex items-center justify-center text-[#d4a373] mb-6 group-hover:scale-110 transition-all duration-300 shadow-inner shrink-0 relative z-10">
                 <Globe size={24} />
               </div>
               <h3 className="text-xl font-bold mb-3 text-[#2d1e18] font-display relative z-10">10+ Languages</h3>
               <p className="text-[#3d2b1f]/80 leading-relaxed font-medium relative z-10">Breaking the language barrier across India natively.</p>
            </div>
            <div className="p-8 rounded-xl bg-[#faedcd] border border-[#faedcd] hover:border-[#d4a373]/50 hover:scale-[1.03] transition-all duration-300 group shadow-sm flex flex-col relative z-10">
               <div className="absolute inset-0 bg-[#fefae0]/40 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none z-0" />
               <div className="w-12 h-12 rounded-xl bg-[#d4a373]/20 flex items-center justify-center text-[#d4a373] mb-6 group-hover:scale-110 transition-all duration-300 shadow-inner shrink-0 relative z-10">
                 <Cpu size={24} />
               </div>
               <h3 className="text-xl font-bold mb-3 text-[#2d1e18] font-display relative z-10">Sub-second Latency</h3>
               <p className="text-[#3d2b1f]/80 leading-relaxed font-medium relative z-10">Human-like response speeds using cutting edge models.</p>
            </div>
          </motion.div>
        </div>
      </section>

      {/* The Flow Section */}
      <section className="relative z-10 py-24 px-6 max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-black mb-6 text-[#2d1e18] font-display leading-tight">A Bounded Recovery Workflow</h2>
          <p className="text-[#3d2b1f]/80 max-w-2xl mx-auto text-lg font-medium">
            Detect → Diagnose → Decide → Act → Recover, with stopping rules and a complete audit timeline.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {steps.map((step, idx) => (
            <motion.div
              key={idx}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              viewport={{ once: true }}
              className="p-8 rounded-xl bg-[#faedcd] border border-[#faedcd] hover:border-[#d4a373]/50 hover:scale-[1.03] transition-all duration-300 group shadow-sm flex flex-col relative z-10"
            >
              <div className="absolute inset-0 bg-[#fefae0]/40 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none z-0" />
              <div className="w-12 h-12 rounded-xl bg-[#d4a373]/20 flex items-center justify-center text-[#d4a373] mb-6 group-hover:scale-110 transition-all duration-300 shadow-inner shrink-0 relative z-10">
                <step.icon size={24} />
              </div>
              <h3 className="text-xl font-bold mb-3 text-[#2d1e18] font-display relative z-10">{step.title}</h3>
              <p className="text-[#3d2b1f]/80 leading-relaxed font-medium relative z-10">{step.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Floating CTA */}
      <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50">
        <motion.div
          initial={{ y: 100 }}
          animate={{ y: 0 }}
          className="px-6 py-4 rounded-xl bg-[#faedcd]/90 backdrop-blur-2xl border border-[#d4a373]/30 flex items-center gap-6 shadow-2xl shadow-[#3d2b1f]/10"
        >
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-sm font-bold text-[#3d2b1f]">System Active</span>
          </div>
          <div className="h-4 w-px bg-[#d4a373]/30" />
          <button
            onClick={handleDashboardClick}
            className="text-sm font-black text-[#d4a373] hover:text-[#b5835a] transition-colors cursor-pointer"
          >
            Launch Dashboard
          </button>
        </motion.div>
      </div>

      <Footer />
    </div>
  );
};

export default LandingPage;
