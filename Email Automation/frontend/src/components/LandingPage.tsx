import React, { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { HeroSection } from './HeroSection';
import { SocialProofBar } from './SocialProofBar';
import { ProblemStatement } from './ProblemStatement';
import { SignupModal } from './SignupModal';
import { Button } from './ui/button';
import { 
  Zap, Mail, MessageSquare, Users, CheckCircle, FileText,
  ChevronLeft, ChevronRight, Play, Calendar, Target, Shield
} from 'lucide-react';

const LandingPage: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [isSignupModalOpen, setIsSignupModalOpen] = useState(false);
  const [currentTestimonialIndex, setCurrentTestimonialIndex] = useState(0);
  const [openFAQIndex, setOpenFAQIndex] = useState<number | null>(null);

  useEffect(() => {
    if (user) {
      navigate('/dashboard');
    }
  }, [user, navigate]);

  if (user) {
    return null;
  }

  // How It Works Section
  const howItWorks = [
    {
      step: '01',
      title: 'Find the Leads',
      description: 'Use our browser extension to scrape verified leads from LinkedIn, Google Maps, or any website. No account required for basic scraping.',
      icon: Target,
    },
    {
      step: '02',
      title: 'Get AI-Generated Emails',
      description: 'After scraping leads, get personalized AI emails for each lead. Review, tweak, and approve. You maintain full control over your voice.',
      icon: Mail,
    },
    {
      step: '03',
      title: 'Close the Deal',
      description: 'Send your approved emails. Our automation handles follow-ups until they reply. You focus on closing the high-ticket contracts.',
      icon: CheckCircle,
    },
  ];

  // Features Section
  const features = [
    {
      icon: Zap,
      title: 'Draft-to-Send Workflow',
      description: 'We hand you a personalized, context-aware draft. You review, approve, and own the relationship.',
    },
    {
      icon: Shield,
      title: 'Trust Stack',
      description: 'We handle SPF, DKIM, DMARC to ensure 99.9% inbox delivery rate. Your emails get seen, not filtered.',
    },
    {
      icon: MessageSquare,
      title: 'Automated Follow-ups',
      description: 'Once you send the first message, our automation maintains contact with persistent follow-ups until the deal closes.',
    },
    {
      icon: Users,
      title: 'Semi-Automated Control',
      description: 'Automation handles the search; you handle the human touch. Maintain 100% control over the first impression.',
    },
    {
      icon: FileText,
      title: 'Self-Updating Pipeline',
      description: 'The platform updates your contacts and deal status automatically based on your real email activity.',
    },
    {
      icon: Calendar,
      title: 'Meeting Scheduling',
      description: 'Automated meeting booking with conflict detection. Natural language parsing for easy scheduling.',
    },
  ];

  // Testimonials
  const testimonials = [
    {
      quote: "Booked 12 meetings in one week. Closed 3 deals worth $45K. This tool paid for itself in the first month.",
      author: "Marcus Rodriguez",
      role: "Marketing Consultant",
      metric: "+$45K Revenue"
    },
    {
      quote: "Saved 20 hours per week on outreach. Went from closing 2 deals a month to 6 deals. My revenue tripled.",
      author: "Jessica Park",
      role: "Copywriter",
      metric: "3x Revenue"
    },
    {
      quote: "I scraped 500 LinkedIn leads in 2 hours and sent personalized emails to all of them. Booked 47 meetings and closed $50K in new business.",
      author: "David Thompson",
      role: "Business Consultant",
      metric: "47 Meetings"
    },
  ];

  // FAQ Section
  const faqs = [
    {
      question: "What is semi-automated outreach?",
      answer: "Semi-automated outreach means we automate the lead discovery and email drafting, but you review and approve every message before it's sent. This gives you the speed of automation with the control of personalization."
    },
    {
      question: "How does WolfAssistants ensure high deliverability?",
      answer: "We handle all the technical setup including SPF, DKIM, and DMARC configuration. We also monitor your sending patterns and throttle speeds to maintain a 99.9% inbox delivery rate."
    },
    {
      question: "Is WolfAssistants suitable for my business?",
      answer: "WolfAssistants is perfect for B2B consultants, agency owners, freelancers, and any professional who needs to scale their outreach without losing the personal touch. If you're sending 10+ emails per week, you'll benefit."
    },
    {
      question: "What if I need help?",
      answer: "We offer email support, comprehensive documentation, and video tutorials. Our team is responsive and committed to helping you succeed with the platform."
    },
  ];

  return (
    <div className="min-h-screen bg-white">
      <HeroSection />
      <SocialProofBar />
      <ProblemStatement />

      {/* Proof Section */}
      <section className="py-16 bg-white">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <p className="text-2xl md:text-3xl font-semibold text-gray-900 mb-3">
            "John booked 12 meetings last week using our system"
          </p>
          <p className="text-lg text-gray-600">
            — Real customer, real results. <a href="#case-study" className="underline hover:text-blue-600 transition-colors text-blue-600">See case study →</a>
          </p>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-24 px-6 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold mb-4 text-gray-900">
              How It Works
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Three simple steps to close more deals
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {howItWorks.map((step, index) => {
              const Icon = step.icon;
              return (
                <div key={index} className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 text-center hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-center w-14 h-14 rounded-lg bg-blue-100 text-blue-600 mb-6 mx-auto">
                    <Icon className="w-7 h-7" />
                  </div>
                  <div className="text-sm font-semibold text-blue-600 mb-2">{step.step}</div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-3">{step.title}</h3>
                  <p className="text-gray-600 leading-relaxed">{step.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Video Demo Section */}
      <section className="py-24 px-6 bg-white">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-4xl md:text-5xl font-bold mb-4 text-gray-900">
              See It In Action
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Watch how WolfAssistants turns LinkedIn profiles into booked meetings in 15 minutes
            </p>
          </div>

          <div className="aspect-video bg-gray-100 rounded-xl border border-gray-200 overflow-hidden relative group cursor-pointer">
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="w-20 h-20 mx-auto mb-4 bg-blue-600 rounded-full flex items-center justify-center group-hover:scale-110 transition-transform shadow-lg">
                  <Play className="w-10 h-10 text-white ml-1" fill="currentColor" />
                </div>
                <p className="text-gray-900 font-semibold">Watch Demo Video</p>
                <p className="text-gray-500 text-sm mt-2">(Video placeholder)</p>
              </div>
            </div>
          </div>

          <div className="mt-8 text-center">
            <Button
              onClick={() => setIsSignupModalOpen(true)}
              className="px-8 py-4 text-base font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-sm"
            >
              Start Free Trial
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 px-6 bg-gray-50">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold mb-4 text-gray-900">
              Everything You Need to Scale
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              All the tools you need to find leads, personalize outreach, and close deals—in one platform
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              return (
                <div key={index} className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-center w-12 h-12 rounded-lg bg-blue-100 text-blue-600 mb-4">
                    <Icon className="w-6 h-6" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
                  <p className="text-gray-600 text-sm leading-relaxed">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Case Study Section */}
      <section className="py-24 px-6 bg-white" id="case-study">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold mb-4 text-gray-900">
              Real Results
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              How Sarah closed $50K in new business using WolfAssistants
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
            <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 text-center">
              <div className="text-4xl font-bold text-blue-600 mb-2">500</div>
              <div className="text-lg font-semibold text-gray-900 mb-1">Leads Scraped</div>
              <div className="text-sm text-gray-600">In 2 hours</div>
            </div>
            <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 text-center">
              <div className="text-4xl font-bold text-blue-600 mb-2">47</div>
              <div className="text-lg font-semibold text-gray-900 mb-1">Meetings Booked</div>
              <div className="text-sm text-gray-600">From personalized emails</div>
            </div>
            <div className="bg-white p-8 rounded-xl shadow-sm border border-gray-200 text-center">
              <div className="text-4xl font-bold text-blue-600 mb-2">$50K</div>
              <div className="text-lg font-semibold text-gray-900 mb-1">New Revenue</div>
              <div className="text-sm text-gray-600">In first 30 days</div>
            </div>
          </div>

          <div className="bg-white p-8 md:p-12 rounded-xl shadow-sm border border-gray-200">
            <div className="space-y-6 text-gray-600">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Week 1</h3>
                <p>Sarah installed our browser extension and scraped 500 leads from LinkedIn and Google Maps in 2 hours. She used our AI to generate personalized opening emails for each lead.</p>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Week 2</h3>
                <p>Sent 200 personalized emails using our draft-to-send workflow. She reviewed and approved each message, maintaining her personal touch while saving 15+ hours.</p>
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Week 3-4</h3>
                <p>Our automated follow-up system kicked in. Sarah booked 47 meetings from the initial outreach. She closed 3 high-ticket clients worth $50K in new business.</p>
              </div>
            </div>
            <div className="mt-8 pt-8 border-t border-gray-200">
              <p className="text-xl font-semibold text-gray-900 mb-2">
                "This tool paid for itself in the first week. I'm closing 3x more deals with half the effort."
              </p>
              <p className="text-gray-600">
                — Sarah Chen, Marketing Consultant
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-24 px-6 bg-gray-50">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-4xl md:text-5xl font-bold mb-4 text-gray-900">
              What Our Customers Say
            </h2>
          </div>

          <div className="relative">
            <div className="overflow-hidden">
              <div 
                className="flex transition-transform duration-500 ease-in-out"
                style={{ transform: `translateX(-${currentTestimonialIndex * 100}%)` }}
              >
                {testimonials.map((testimonial, index) => (
                  <div key={index} className="min-w-full px-4">
                    <div className="bg-white p-8 md:p-12 rounded-xl shadow-sm border border-gray-200 text-center">
                      <div className="text-6xl text-blue-100 mb-6">"</div>
                      <blockquote className="text-xl md:text-2xl text-gray-900 mb-6 leading-relaxed">
                        {testimonial.quote}
                      </blockquote>
                      <div className="inline-block px-4 py-2 bg-blue-100 text-blue-600 rounded-lg text-sm font-semibold mb-4">
                        {testimonial.metric}
                      </div>
                      <footer className="text-gray-600">
                        <div className="font-semibold text-gray-900">{testimonial.author}</div>
                        <div className="text-sm">{testimonial.role}</div>
                      </footer>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-center gap-4 mt-8">
              <button
                onClick={() => setCurrentTestimonialIndex((prev) => 
                  prev === 0 ? testimonials.length - 1 : prev - 1
                )}
                className="w-12 h-12 rounded-lg border border-gray-300 hover:border-gray-400 bg-white flex items-center justify-center text-gray-700 transition-colors shadow-sm"
                aria-label="Previous testimonial"
              >
                <ChevronLeft className="w-6 h-6" />
              </button>

              <div className="flex gap-2">
                {testimonials.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentTestimonialIndex(index)}
                    className={`h-2 transition-all ${
                      index === currentTestimonialIndex
                        ? 'w-8 bg-blue-600'
                        : 'w-2 bg-gray-300 hover:bg-gray-400'
                    } rounded-full`}
                    aria-label={`Go to testimonial ${index + 1}`}
                  />
                ))}
              </div>

              <button
                onClick={() => setCurrentTestimonialIndex((prev) => 
                  prev === testimonials.length - 1 ? 0 : prev + 1
                )}
                className="w-12 h-12 rounded-lg border border-gray-300 hover:border-gray-400 bg-white flex items-center justify-center text-gray-700 transition-colors shadow-sm"
                aria-label="Next testimonial"
              >
                <ChevronRight className="w-6 h-6" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-24 px-6 bg-white">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-4xl md:text-5xl font-bold mb-4 text-gray-900">
              Frequently Asked Questions
            </h2>
          </div>

          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <div 
                key={index} 
                className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow"
              >
                <button
                  className="w-full p-6 text-left flex items-center justify-between gap-4 focus:outline-none"
                  onClick={() => setOpenFAQIndex(openFAQIndex === index ? null : index)}
                  aria-expanded={openFAQIndex === index}
                >
                  <h3 className="text-lg font-semibold text-gray-900 pr-4">{faq.question}</h3>
                  <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
                    openFAQIndex === index ? 'bg-blue-600 rotate-180' : 'bg-gray-100'
                  }`}>
                    <ChevronRight className={`w-5 h-5 ${openFAQIndex === index ? 'text-white' : 'text-gray-600'}`} />
                  </div>
                </button>
                {openFAQIndex === index && (
                  <div className="px-6 pb-6 text-gray-600 leading-relaxed">
                    {faq.answer}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA Section */}
      <section className="py-24 px-6 bg-blue-600">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-4xl md:text-5xl font-bold mb-4 text-white">
            Ready to Close More Deals?
          </h2>
          <p className="text-lg text-blue-100 mb-8 max-w-2xl mx-auto">
            Start your free trial today. No credit card required. Cancel anytime.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Button
              onClick={() => setIsSignupModalOpen(true)}
              size="lg"
              className="px-8 py-4 text-base font-semibold bg-white hover:bg-gray-100 text-blue-600 rounded-lg shadow-lg"
            >
              Start Free Trial
            </Button>
            <div className="flex items-center gap-4 text-sm text-blue-100">
              <span className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-300" />
                14-day trial
              </span>
              <span className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-300" />
                Cancel anytime
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 bg-white py-16 px-6" role="contentinfo">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-12 mb-12">
            <div className="md:col-span-2">
              <h3 className="text-2xl font-bold mb-4 text-gray-900">WolfAssistants</h3>
              <p className="text-gray-600 mb-6 max-w-md">
                The all-in-one platform for high-end professionals to automate lead discovery, personalize outreach, and close deals.
              </p>
              <div className="flex gap-4">
                {[
                  { name: 'LinkedIn', url: 'https://www.linkedin.com/company/wolfassistants' },
                  { name: 'Twitter', url: 'https://x.com/wolfassistants' },
                  { name: 'Instagram', url: 'https://www.instagram.com/wolfassistants/' },
                ].map((social) => (
                  <a
                    key={social.name}
                    href={social.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-10 h-10 rounded-lg border border-gray-200 hover:border-gray-300 flex items-center justify-center text-gray-600 hover:text-gray-900 transition-colors bg-gray-50 hover:bg-gray-100"
                    aria-label={social.name}
                  >
                    <span className="text-sm">{social.name[0]}</span>
                  </a>
                ))}
              </div>
            </div>
            
            <nav aria-label="Product links">
              <h4 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">Product</h4>
              <ul className="space-y-3 text-gray-600">
                <li><a href="#features" className="hover:text-gray-900 transition-colors">Features</a></li>
                <li><Link to="/pricing" className="hover:text-gray-900 transition-colors">Pricing</Link></li>
                <li><a href="#case-study" className="hover:text-gray-900 transition-colors">Case Studies</a></li>
                <li><a href="/dashboard" className="hover:text-gray-900 transition-colors">Dashboard</a></li>
              </ul>
            </nav>
            
            <nav aria-label="Support links">
              <h4 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wider">Support</h4>
              <ul className="space-y-3 text-gray-600">
                <li><a href="/privacy" className="hover:text-gray-900 transition-colors">Privacy</a></li>
                <li><a href="/terms" className="hover:text-gray-900 transition-colors">Terms</a></li>
                <li><a href="mailto:info@wolfassistants.com" className="hover:text-gray-900 transition-colors">Contact</a></li>
                <li><a href="https://discord.gg/QwbZr6dgnT" target="_blank" rel="noopener noreferrer" className="hover:text-gray-900 transition-colors">Discord</a></li>
              </ul>
            </nav>
          </div>
          
          <div className="border-t border-gray-200 pt-8 flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="text-gray-600 text-sm">
              © 2024 WolfAssistants. All rights reserved.
            </div>
            <div className="flex gap-6 text-xs text-gray-500">
              <span>Lead Generation</span>
              <span>Email Automation</span>
              <span>Sales Outreach</span>
            </div>
          </div>
        </div>
      </footer>
      
      <SignupModal 
        isOpen={isSignupModalOpen} 
        onClose={() => setIsSignupModalOpen(false)} 
      />
    </div>
  );
};

export default LandingPage;
