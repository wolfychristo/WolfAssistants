import { Button } from "./ui/button";

export function HeroSection() {
  const appUrl = process.env.REACT_APP_APP_URL || 'https://app.wolfassistants.com';

  const handleGetStarted = () => {
    // Redirect to app domain for signup
    window.location.href = `${appUrl}/login?signup=true`;
  };

  return (
    <header 
      className="relative min-h-[90vh] flex items-center bg-gradient-to-b from-blue-50 to-white pt-16" 
      role="banner"
    >
      <div className="relative z-10 max-w-7xl mx-auto px-6 lg:px-8 w-full py-20">
        <div className="max-w-4xl mx-auto text-center">
          {/* Badge */}
          <div className="mb-6">
            <span className="inline-block px-4 py-1.5 text-xs font-medium text-blue-600 bg-blue-100 rounded-full">
              Trusted by 7 million users worldwide
            </span>
          </div>

          {/* Main Headline */}
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold mb-6 text-gray-900 leading-tight">
            Send emails and manage replies at scale
          </h1>

          {/* Subheadline */}
          <p className="text-xl sm:text-2xl text-gray-600 mb-10 max-w-3xl mx-auto leading-relaxed">
            WolfAssistants helps you run email campaigns and manage every reply. Right from Gmail, Outlook and the tools you already use.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
            <Button
              onClick={handleGetStarted}
              size="lg"
              className="px-8 py-4 text-base font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-all shadow-lg shadow-blue-600/20"
            >
              Get started for free
            </Button>
            
            <button
              onClick={() => {}}
              className="px-8 py-4 text-base font-semibold text-gray-700 border border-gray-300 hover:border-gray-400 rounded-lg transition-all bg-white hover:bg-gray-50"
            >
              Watch demo
            </button>
          </div>

          {/* Trust Indicators */}
          <div className="flex flex-wrap items-center justify-center gap-8 text-sm text-gray-600">
            <div className="flex items-center gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span>No credit card required</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span>14-day free trial</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-green-600 font-bold">✓</span>
              <span>Cancel anytime</span>
            </div>
          </div>

          {/* Rating */}
          <div className="mt-8 flex items-center justify-center gap-2">
            <div className="flex text-yellow-400">
              {'★'.repeat(5)}
            </div>
            <span className="text-sm text-gray-600 font-medium">
              Rated 4.9/5 out of 11,741+ reviews
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}
