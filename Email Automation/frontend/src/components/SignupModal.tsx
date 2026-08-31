import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Checkbox } from "./ui/checkbox";
import { useAuth } from "../contexts/AuthContext";
import toast from "react-hot-toast";
import { X, ArrowLeft, ArrowRight } from "lucide-react";

interface SignupModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface SignupData {
  fullName: string;
  referralCode: string;
  workEmail: string;
  username: string;
  password: string;
  confirmPassword: string;
  companyName: string;
  jobTitle: string;
  industry: string;
  phoneNumber: string;
  contactsToManage: string;
  purpose: string;
  consent: boolean;
}

export function SignupModal({ isOpen, onClose }: SignupModalProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [signupData, setSignupData] = useState<SignupData>({
    fullName: "",
    referralCode: "",
    workEmail: "",
    username: "",
    password: "",
    confirmPassword: "",
    companyName: "",
    jobTitle: "",
    industry: "",
    phoneNumber: "",
    contactsToManage: "",
    purpose: "",
    consent: false,
  });

  const { register } = useAuth();
  const navigate = useNavigate();

  const totalSteps = 13;

  const updateSignupData = (field: keyof SignupData, value: string | boolean) => {
    setSignupData(prev => ({ ...prev, [field]: value }));
  };

  const nextStep = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const isStepValid = () => {
    switch (currentStep) {
      case 1: return signupData.fullName.trim() !== "";
      case 2: return true; // Referral code is optional
      case 3: return signupData.workEmail.trim() !== "" && signupData.workEmail.includes("@");
      case 4: return signupData.username.trim() !== "" && signupData.username.length >= 3;
      case 5: return signupData.password.trim() !== "" && signupData.password.length >= 8;
      case 6: return signupData.confirmPassword.trim() !== "" && signupData.password === signupData.confirmPassword;
      case 7: return signupData.companyName.trim() !== "";
      case 8: return signupData.jobTitle.trim() !== "";
      case 9: return signupData.industry.trim() !== "";
      case 10: return true; // Phone is optional
      case 11: return signupData.contactsToManage.trim() !== "";
      case 12: return signupData.purpose.trim() !== "";
      case 13: return signupData.consent;
      default: return false;
    }
  };

  const handleSignup = async () => {
    setIsLoading(true);
    
    try {
      const result = await register({
        email: signupData.workEmail,
        password: signupData.password,
        name: signupData.fullName,
        businessName: signupData.companyName,
        company_name: signupData.companyName,
        team_size: signupData.contactsToManage,
        heard_about_us: signupData.purpose,
        // Use the actual username provided by user
        username: signupData.username,
        revenue_size: signupData.industry, // Use industry as revenue size for now
        social_link: "", // Could be added in future steps
        calendly_link: "", // Could be added in future steps
        referral_code: signupData.referralCode, // Include referral code
      });
      
      if (result.success) {
        toast.success("Registration successful! You can now log in with your credentials.");
        onClose();
        navigate("/login");
      } else {
        toast.error(result.message || "Registration failed");
      }
    } catch (error) {
      toast.error("An error occurred during registration");
    } finally {
      setIsLoading(false);
    }
  };

  const renderStep = () => {
    switch (currentStep) {
      case 1:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="fullName" className="text-sm font-medium text-gray-700">
                Full Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="fullName"
                type="text"
                placeholder="Enter your full name"
                value={signupData.fullName}
                onChange={(e) => updateSignupData("fullName", e.target.value)}
                className="h-11 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </div>
            <Button 
              onClick={nextStep} 
              disabled={!isStepValid()}
              className="w-full h-12 text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Continue <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        );

      case 2:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="referralCode" className="text-sm font-medium text-gray-700">
                Referral Code <span className="text-gray-500 text-sm font-normal">(Optional)</span>
              </Label>
              <Input
                id="referralCode"
                type="text"
                placeholder="Enter referral code if you have one"
                value={signupData.referralCode}
                onChange={(e) => updateSignupData("referralCode", e.target.value)}
                className="h-11 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500"
              />
              <p className="text-sm text-gray-600">
                Got a referral code from a friend? Enter it here to get bonus credits!
              </p>
            </div>
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={prevStep}
                className="flex-1 h-11 text-base font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg"
              >
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button 
                onClick={nextStep} 
                disabled={!isStepValid()}
                className="flex-1 h-11 text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      case 3:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="workEmail" className="text-base font-medium">
                Work Email Address <span className="text-red-500">*</span>
              </Label>
              <Input
                id="workEmail"
                type="email"
                placeholder="Enter your work email"
                value={signupData.workEmail}
                onChange={(e) => updateSignupData("workEmail", e.target.value)}
                className="h-12 text-base"
                required
              />
            </div>
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={prevStep}
                className="flex-1 h-11 text-base font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg"
              >
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button 
                onClick={nextStep} 
                disabled={!isStepValid()}
                className="flex-1 h-11 text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      case 4:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-sm font-medium text-gray-700">
                Username <span className="text-red-500">*</span>
              </Label>
              <Input
                id="username"
                type="text"
                placeholder="Choose a unique username"
                value={signupData.username}
                onChange={(e) => updateSignupData("username", e.target.value)}
                className="h-11 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                required
              />
              <p className="text-sm text-gray-600">Must be at least 3 characters long</p>
            </div>
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={prevStep}
                className="flex-1 h-11 text-base font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg"
              >
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button 
                onClick={nextStep} 
                disabled={!isStepValid()}
                className="flex-1 h-11 text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      case 5:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="password" className="text-sm font-medium text-gray-700">
                Password <span className="text-red-500">*</span>
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="Create a strong password"
                value={signupData.password}
                onChange={(e) => updateSignupData("password", e.target.value)}
                className="h-11 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                required
              />
              <p className="text-sm text-gray-600">Must be at least 8 characters long</p>
            </div>
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={prevStep}
                className="flex-1 h-11 text-base font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg"
              >
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button 
                onClick={nextStep} 
                disabled={!isStepValid()}
                className="flex-1 h-11 text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      case 6:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="confirmPassword" className="text-sm font-medium text-gray-700">
                Confirm Password <span className="text-red-500">*</span>
              </Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="Confirm your password"
                value={signupData.confirmPassword}
                onChange={(e) => updateSignupData("confirmPassword", e.target.value)}
                className="h-11 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                required
              />
              {signupData.confirmPassword && signupData.password !== signupData.confirmPassword && (
                <p className="text-sm text-red-600">Passwords do not match</p>
              )}
            </div>
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={prevStep}
                className="flex-1 h-11 text-base font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg"
              >
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button 
                onClick={nextStep} 
                disabled={!isStepValid()}
                className="flex-1 h-11 text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      case 7:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="companyName" className="text-sm font-medium text-gray-700">
                Company Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="companyName"
                type="text"
                placeholder="Enter your company name"
                value={signupData.companyName}
                onChange={(e) => updateSignupData("companyName", e.target.value)}
                className="h-11 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </div>
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={prevStep}
                className="flex-1 h-11 text-base font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg"
              >
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button 
                onClick={nextStep} 
                disabled={!isStepValid()}
                className="flex-1 h-11 text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      case 8:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="jobTitle" className="text-sm font-medium text-gray-700">
                Job Title/Role <span className="text-red-500">*</span>
              </Label>
              <Input
                id="jobTitle"
                type="text"
                placeholder="e.g., Sales Manager, Marketing Director"
                value={signupData.jobTitle}
                onChange={(e) => updateSignupData("jobTitle", e.target.value)}
                className="h-11 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </div>
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={prevStep}
                className="flex-1 h-11 text-base font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg"
              >
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button 
                onClick={nextStep} 
                disabled={!isStepValid()}
                className="flex-1 h-11 text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      case 9:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="industry" className="text-sm font-medium text-gray-700">
                Industry <span className="text-red-500">*</span>
              </Label>
              <Input
                id="industry"
                type="text"
                placeholder="e.g., Technology, Healthcare, Finance"
                value={signupData.industry}
                onChange={(e) => updateSignupData("industry", e.target.value)}
                className="h-11 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </div>
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={prevStep}
                className="flex-1 h-11 text-base font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg"
              >
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button 
                onClick={nextStep} 
                disabled={!isStepValid()}
                className="flex-1 h-11 text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      case 10:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="phoneNumber" className="text-sm font-medium text-gray-700">
                Phone Number <span className="text-gray-500 text-sm font-normal">(Optional)</span>
              </Label>
              <Input
                id="phoneNumber"
                type="tel"
                placeholder="Enter your phone number"
                value={signupData.phoneNumber}
                onChange={(e) => updateSignupData("phoneNumber", e.target.value)}
                className="h-11 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500"
              />
            </div>
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={prevStep}
                className="flex-1 h-12 text-base font-medium"
              >
                <ArrowLeft className="mr-2 h-4 w-4" /> Previous
              </Button>
              <Button 
                onClick={nextStep} 
                className="flex-1 h-12 text-base font-medium"
              >
                Next <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      case 11:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="contactsToManage" className="text-sm font-medium text-gray-700">
                Number of Contacts to Manage <span className="text-red-500">*</span>
              </Label>
              <Input
                id="contactsToManage"
                type="text"
                placeholder="e.g., 100-500, 500-1000, 1000+"
                value={signupData.contactsToManage}
                onChange={(e) => updateSignupData("contactsToManage", e.target.value)}
                className="h-11 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </div>
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={prevStep}
                className="flex-1 h-11 text-base font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg"
              >
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button 
                onClick={nextStep} 
                disabled={!isStepValid()}
                className="flex-1 h-11 text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      case 12:
        return (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="purpose" className="text-sm font-medium text-gray-700">
                Purpose of Using the Tool <span className="text-red-500">*</span>
              </Label>
              <Input
                id="purpose"
                type="text"
                placeholder="e.g., Sales, Marketing, Recruitment"
                value={signupData.purpose}
                onChange={(e) => updateSignupData("purpose", e.target.value)}
                className="h-11 text-base border-gray-300 focus:border-blue-500 focus:ring-blue-500"
                required
              />
            </div>
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={prevStep}
                className="flex-1 h-11 text-base font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg"
              >
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button 
                onClick={nextStep} 
                disabled={!isStepValid()}
                className="flex-1 h-11 text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          </div>
        );

      case 13:
        return (
          <div className="space-y-4">
            <div className="space-y-4">
              <div className="flex items-start space-x-3">
                <Checkbox
                  id="consent"
                  checked={signupData.consent}
                  onChange={(e) => updateSignupData("consent", e.target.checked)}
                  className="mt-1"
                />
                <Label htmlFor="consent" className="text-sm leading-relaxed text-gray-700 cursor-pointer">
                  I consent to the{" "}
                  <button 
                    type="button"
                    className="text-blue-600 hover:text-blue-700 hover:underline bg-transparent border-none p-0 cursor-pointer font-medium"
                    onClick={() => {
                      // TODO: Open data processing policy modal/page
                      toast.success('Data processing policy will be shown here');
                    }}
                  >
                    data processing
                  </button>{" "}
                  and{" "}
                  <button 
                    type="button"
                    className="text-blue-600 hover:text-blue-700 hover:underline bg-transparent border-none p-0 cursor-pointer font-medium"
                    onClick={() => {
                      // TODO: Open privacy policy modal/page
                      toast.success('Privacy policy will be shown here');
                    }}
                  >
                    privacy policy
                  </button>{" "}
                  <span className="text-red-500">*</span>
                </Label>
              </div>
            </div>
            <div className="flex gap-3">
              <Button 
                variant="outline" 
                onClick={prevStep}
                className="flex-1 h-11 text-base font-medium bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 rounded-lg"
              >
                <ArrowLeft className="mr-2 h-4 w-4" /> Back
              </Button>
              <Button 
                onClick={handleSignup} 
                disabled={!isStepValid() || isLoading}
                className="flex-1 h-11 text-base font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? "Creating account..." : "Create account"}
              </Button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[100] p-4 backdrop-blur-sm">
      <Card className="w-full max-w-lg relative bg-white rounded-xl shadow-2xl border border-gray-200">
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-4 right-4 h-8 w-8 p-0 hover:bg-gray-100 rounded-lg text-gray-600"
          onClick={onClose}
        >
          <X className="h-5 w-5" />
        </Button>
        
        <CardHeader className="text-center pt-8 pb-6 px-8">
          <CardTitle className="text-3xl font-bold text-gray-900 mb-2">
            Create your account
          </CardTitle>
          <CardDescription className="text-gray-600 text-sm">
            Step {currentStep} of {totalSteps}
          </CardDescription>
          
          {/* Progress bar */}
          <div className="w-full bg-gray-100 rounded-full h-2 mt-6">
            <div 
              className="bg-blue-600 h-full rounded-full transition-all duration-500"
              style={{ width: `${(currentStep / totalSteps) * 100}%` }}
            ></div>
          </div>
        </CardHeader>
        
        <CardContent className="px-8 pb-8">
          {renderStep()}
        </CardContent>
      </Card>
    </div>
  );
}
