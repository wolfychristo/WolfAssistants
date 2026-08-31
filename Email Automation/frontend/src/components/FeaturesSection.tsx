import { Card, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Button } from "./ui/button";
import { Zap, MessageSquare, Mail, Users, FileText, CheckCircle, ArrowRight, ChevronDown, ChevronUp, ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { SignupModal } from "./SignupModal";

export function FeaturesSection() {
  const navigate = useNavigate();
  const [isSignupModalOpen, setIsSignupModalOpen] = useState(false);
  const [openFAQIndex, setOpenFAQIndex] = useState<number | null>(null);
  const [currentTestimonialIndex, setCurrentTestimonialIndex] = useState(0);

  const features = [
    {
      icon: Zap,
      title: "Draft-to-Send Workflow",
      description: "We don't automate your voice. We hand you a personalized, context-aware draft. You review, you approve, you own the relationship."
    },
    {
      icon: Mail,
      title: "The Trust Stack",
      description: "We handle the technical heavy lifting - SPF, DKIM, DMARC. We ensure your reputation is bulletproof so you land in the primary inbox, every time."
    },
    {
      icon: MessageSquare,
      title: "Automated Chase",
      description: "Once you send the first message, our automation engine takes over. Persistent, high-value follow-ups that maintain contact until the deal is closed."
    },
    {
      icon: Users,
      title: "Semi-Automated Control",
      description: "Automation handles the search; you handle the human touch. Maintain 100% control over the first impression while we automate the persistence."
    },
    {
      icon: CheckCircle,
      title: "Client Discovery Engine",
      description: "Extract verified emails and LinkedIn profiles directly from Google Maps and websites. No more manual searching; just high-value leads."
    },
    {
      icon: FileText,
      title: "Self-Updating Pipeline",
      description: "Forget manual CRM entry. The platform updates your contacts and deal status automatically based on your real email activity."
    }
  ];

  const benefits = [
    "Build a bulletproof Trust Stack for 99.9% inbox delivery rate.",
    "Maintain Semi-Automated Control over every first impression.",
    "Automate the chase with persistent, high-value follow-ups.",
    "Hand the 'Outreach' work to automation; focus only on The Close."
  ];

  const howItWorks = [
    {
      step: "1",
      title: "Find the Leads",
      description: "Use our extension to grab verified leads from Google Maps, LinkedIn, or any website."
    },
    {
      step: "2",
      title: "Review & Send",
      description: "Review our AI-generated personalized opening; hit send when you're ready."
    },
    {
      step: "3",
      title: "Close the Deal",
      description: "Our automation engine handles the follow-up until the contract is signed."
    }
  ];

  const testimonials = [
    {
      quote: "Booked 12 meetings in one week. Closed 3 deals worth $45K. This tool paid for itself in the first month.",
      author: "Marcus Rodriguez, Marketing Consultant"
    },
    {
      quote: "Saved 20 hours per week on outreach. Went from closing 2 deals a month to 6 deals. My revenue tripled.",
      author: "Jessica Park, Copywriter"
    },
    {
      quote: "I scraped 500 LinkedIn leads in 2 hours and sent personalized emails to all of them. Booked 47 meetings and closed $50K in new business.",
      author: "David Thompson, Business Consultant"
    }
  ];

  const pricingPlans = [
    {
      name: "Early Adopter",
      price: "$0",
      period: "/forever",
      description: "Full access to AI drafts, 1 mailbox, and lead extraction. Free for our first 500 users.",
      popular: true
    },
    {
      name: "Professional",
      price: "$29",
      period: "/mo",
      description: "Coming soon: Unlimited mailboxes, advanced analytics, and team collaboration.",
      popular: false
    }
  ];

  const faqs = [
    {
      question: "Does WolfAssistants send emails on my behalf?",
      answer: "Yes, but only with your permission. We connect to your email via SMTP/IMAP, draft the messages, and you hit the final 'Send' button."
    },
    {
      question: "Is this just another AI spam tool?",
      answer: "Absolutely not. We hate spam. Our goal is to help you build real relationships through thoughtful, personalized communication that happens to be AI-assisted."
    },
    {
      question: "What platforms does the extension work on?",
      answer: "Our extension works best on LinkedIn, Google Maps, and any business website. It's designed to find contact info wherever you're looking for leads."
    },
    {
      question: "How do you protect my email reputation?",
      answer: "We monitor your deliverability settings (SPF/DKIM/DMARC) and throttle sending speeds to ensure your emails stay out of the spam folder."
    }
  ];

  const toggleFAQ = (index: number) => {
    setOpenFAQIndex(openFAQIndex === index ? null : index);
  };

  return (
    <main className="bg-brand-night">
      {/* Value Proposition */}
      <section className="py-24 md:py-32 px-4 bg-brand-white" aria-labelledby="value-proposition-heading">
        <div className="max-w-4xl mx-auto text-center">
          <h2 id="value-proposition-heading" className="text-5xl md:text-7xl font-black mb-8 tracking-tighter text-brand-black uppercase">
            Land 3 New Clients This Month <br /> <span className="text-brand-red italic">Without Spending 20 Hours on Outreach</span>
          </h2>
          <p className="text-xl md:text-2xl text-gray-600 max-w-3xl mx-auto leading-relaxed font-medium">
            We help B2B consultants, agency owners, and freelancers close 3x more deals by turning LinkedIn profiles into paying clients in 15 minutes instead of 3 days.
          </p>
        </div>
      </section>

      {/* Features - Stacking Tiles */}
      <section className="py-24 md:py-32 px-4 relative" aria-labelledby="features-heading">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-24">
            <h2 id="features-heading" className="text-5xl md:text-7xl font-black mb-6 text-brand-white tracking-tighter uppercase">
              The <span className="text-brand-red">Discovery</span> System.
            </h2>
          </div>
        
          <div className="space-y-[30vh] pb-[30vh]">
            {/* Tile 1: Find the Leads */}
            <div className="sticky top-24 bg-brand-white rounded-[2.5rem] border-l-[12px] border-brand-red p-12 md:p-16 shadow-2xl flex flex-col md:flex-row gap-12 items-center min-h-[500px]">
              <div className="flex-1">
                <span className="text-brand-red font-black text-7xl italic opacity-10">01</span>
                <h3 className="text-4xl md:text-5xl font-black mt-4 text-brand-black uppercase tracking-tighter">Find the Leads</h3>
                <p className="text-xl md:text-2xl mt-6 text-gray-700 leading-relaxed font-medium">
                  Target LinkedIn, Google Maps, or niche sites. We extract verified data and build your <strong className="text-brand-red">Trust Stack</strong> before you even blink.
                </p>
              </div>
              <div className="flex-1 w-full aspect-video bg-gray-100 rounded-3xl border-2 border-dashed border-gray-300 flex items-center justify-center overflow-hidden">
                 <div className="text-gray-400 font-black italic text-xl uppercase tracking-widest">Reconnaissance_UI</div>
              </div>
            </div>

            {/* Tile 2: The Chase (Stacked) */}
            <div className="sticky top-32 bg-brand-black text-brand-white rounded-[2.5rem] border-l-[12px] border-brand-red p-12 md:p-16 shadow-2xl flex flex-col md:flex-row gap-12 items-center min-h-[500px]">
              <div className="flex-1">
                <span className="text-brand-red font-black text-7xl italic opacity-20">02</span>
                <h3 className="text-4xl md:text-5xl font-black mt-4 uppercase tracking-tighter">The Chase</h3>
                <p className="text-xl md:text-2xl mt-6 text-gray-400 leading-relaxed font-medium">
                  Once you send the first message, our automation engine takes over. Persistent, high-value follow-ups that maintain contact until the deal is closed.
                </p>
              </div>
              <div className="flex-1 w-full aspect-video bg-white/5 rounded-3xl border-2 border-dashed border-white/10 flex items-center justify-center overflow-hidden">
                 <div className="text-brand-white/20 font-black italic text-xl uppercase tracking-widest">Automated_Chase_Engine</div>
              </div>
            </div>

            {/* Tile 3: Close the Deal (Final Stack) */}
            <div className="sticky top-40 bg-brand-red text-brand-white rounded-[2.5rem] p-12 md:p-16 shadow-2xl flex flex-col md:flex-row gap-12 items-center min-h-[500px]">
              <div className="flex-1">
                <span className="text-brand-black font-black text-7xl italic opacity-20">03</span>
                <h3 className="text-4xl md:text-5xl font-black mt-4 text-brand-black uppercase tracking-tighter">Close the Deal</h3>
                <p className="text-xl md:text-2xl mt-6 leading-relaxed font-bold">
                  We automate the search; you handle the human touch. When they reply, you're ready to close the high-end contract with semi-automated control.
                </p>
                <Button 
                  size="lg"
                  className="mt-10 h-16 px-12 bg-brand-black text-brand-white font-black text-2xl rounded-2xl hover:scale-105 transition-transform border-none uppercase tracking-tighter"
                  onClick={() => setIsSignupModalOpen(true)}
                >
                  Try Free → Scrape 50 Leads Today
                </Button>
              </div>
              <div className="flex-1 w-full aspect-video bg-black/10 rounded-3xl border-2 border-dashed border-black/20 flex items-center justify-center overflow-hidden">
                 <div className="text-black/30 font-black italic text-xl uppercase tracking-widest">The_Close_Dashboard</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits - Redesigned */}
      <section className="py-24 md:py-32 px-4 bg-brand-white" aria-labelledby="benefits-heading">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-20 items-center">
            <div>
              <h2 id="benefits-heading" className="text-5xl md:text-6xl font-black mb-10 text-brand-black tracking-tighter uppercase leading-none">
                Why the <br /> <span className="text-brand-red">Elite Pack</span> <br /> joins us.
              </h2>
              <ul className="space-y-10" role="list">
                {benefits.map((benefit, index) => (
                  <li key={index} className="flex items-start gap-6 group" role="listitem">
                    <div className="flex-shrink-0 mt-1">
                      <div className="w-10 h-10 bg-brand-red flex items-center justify-center text-brand-white group-hover:rotate-12 transition-transform shadow-[4px_4px_0px_#000]">
                        <CheckCircle className="w-6 h-6" aria-hidden="true" />
                      </div>
                    </div>
                    <p className="text-2xl text-gray-800 leading-tight font-black uppercase tracking-tight">
                      {benefit}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
            <div className="relative aspect-square rounded-[3rem] bg-brand-black border-[12px] border-gray-100 overflow-hidden flex items-center justify-center italic text-brand-white/10 font-black text-4xl text-center p-12">
              [THE_WOLFY_ADVANTAGE_VISUAL]
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials - Simplified & High Contrast */}
      <section className="py-24 md:py-32 px-4 bg-brand-night" aria-labelledby="testimonials-heading">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-20">
            <h2 id="testimonials-heading" className="text-5xl md:text-7xl font-black mb-4 text-brand-white tracking-tighter uppercase">
              Field <span className="text-brand-red italic">Reports.</span>
            </h2>
          </div>
          
          <div className="relative">
            <div className="overflow-hidden">
              <div 
                className="flex transition-transform duration-700 ease-[cubic-bezier(0.87,0,0.13,1)]"
                style={{ transform: `translateX(-${currentTestimonialIndex * 100}%)` }}
              >
                {testimonials.map((testimonial, index) => (
                  <div key={index} className="min-w-full px-4" role="listitem">
                    <div className="p-12 md:p-24 bg-brand-white text-brand-black rounded-[3rem] text-center relative overflow-hidden shadow-[12px_12px_0px_#e32625]">
                      <div className="absolute top-10 left-10 text-[12rem] font-black text-gray-100 leading-none pointer-events-none select-none">“</div>
                      <blockquote className="text-3xl md:text-5xl font-black mb-12 italic tracking-tight leading-tight relative z-10 uppercase">
                        {testimonial.quote}
                      </blockquote>
                      <footer className="text-2xl font-black text-brand-red relative z-10 uppercase tracking-widest">
                        — {testimonial.author}
                      </footer>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-center gap-8 mt-16">
              <Button
                variant="outline"
                size="icon"
                onClick={() => setCurrentTestimonialIndex((prev) => 
                  prev === 0 ? testimonials.length - 1 : prev - 1
                )}
                className="rounded-none h-16 w-16 border-4 border-brand-white text-brand-white hover:bg-brand-red hover:border-brand-red transition-all"
                aria-label="Previous field report"
              >
                <ChevronLeft className="h-8 w-8" />
              </Button>

              <div className="flex gap-4">
                {testimonials.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentTestimonialIndex(index)}
                    className={`h-4 transition-all duration-500 ${
                      index === currentTestimonialIndex
                        ? 'w-16 bg-brand-red'
                        : 'w-4 bg-white/20 hover:bg-white/40'
                    }`}
                    aria-selected={index === currentTestimonialIndex}
                    role="tab"
                  />
                ))}
              </div>

              <Button
                variant="outline"
                size="icon"
                onClick={() => setCurrentTestimonialIndex((prev) => 
                  prev === testimonials.length - 1 ? 0 : prev + 1
                )}
                className="rounded-none h-16 w-16 border-4 border-brand-white text-brand-white hover:bg-brand-red hover:border-brand-red transition-all"
                aria-label="Next field report"
              >
                <ChevronRight className="h-8 w-8" />
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ - High Contrast */}
      <section className="py-24 md:py-32 px-4 bg-brand-white" aria-labelledby="faq-heading">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-20">
            <h2 id="faq-heading" className="text-5xl md:text-7xl font-black mb-4 text-brand-black tracking-tighter uppercase">
              Intel <span className="text-brand-red">Briefing.</span>
            </h2>
          </div>
          <div className="space-y-6" role="list">
            {faqs.map((faq, index) => (
              <div 
                key={index} 
                className="bg-brand-night text-brand-white rounded-2xl overflow-hidden border-2 border-brand-black hover:border-brand-red transition-all duration-300"
                role="listitem"
              >
                <button
                  className="w-full p-8 text-left flex items-center justify-between gap-6 focus:outline-none"
                  onClick={() => toggleFAQ(index)}
                  aria-expanded={openFAQIndex === index}
                >
                  <h3 className="text-2xl font-black uppercase tracking-tight pr-4">{faq.question}</h3>
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center transition-transform duration-500 ${openFAQIndex === index ? 'rotate-180 bg-brand-red' : 'bg-white/10'}`}>
                    <ChevronDown className="w-6 h-6 text-white" />
                  </div>
                </button>
                {openFAQIndex === index && (
                  <div className="px-8 pb-8 text-xl text-gray-400 leading-relaxed font-medium animate-in slide-in-from-top-4 duration-500">
                    {faq.answer}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      <SignupModal 
        isOpen={isSignupModalOpen} 
        onClose={() => setIsSignupModalOpen(false)} 
      />
    </main>
  );
}
