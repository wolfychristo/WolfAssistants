import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import { HeroSection } from './components/HeroSection';
import { SocialProofBar } from './components/SocialProofBar';
import { ProblemStatement } from './components/ProblemStatement';

function HomePage() {
  return (
    <>
      <HeroSection />
      <SocialProofBar />
      <ProblemStatement />
    </>
  );
}

function App() {
  return (
    <Router>
      <div className="App">
        <Navbar />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/contacts" element={<div className="pt-16 min-h-screen flex items-center justify-center"><h1 className="text-4xl font-bold">Contacts Page</h1></div>} />
          <Route path="/features" element={<div className="pt-16 min-h-screen flex items-center justify-center"><h1 className="text-4xl font-bold">Features Page</h1></div>} />
          <Route path="/pricing" element={<div className="pt-16 min-h-screen flex items-center justify-center"><h1 className="text-4xl font-bold">Pricing Page</h1></div>} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
