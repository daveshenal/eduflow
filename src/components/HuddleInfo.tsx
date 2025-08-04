import React, { useState, useEffect } from 'react';
import { ChevronDown, X } from 'lucide-react';

// Custom Select Component
type CustomSelectOption = string | { label: string; value: string; description?: string };
type CustomSelectProps = {
  id: string;
  defaultText: string;
  options: CustomSelectOption[];
  onSelect?: (value: string) => void;
  selectedValue?: string;
};

const CustomSelect: React.FC<CustomSelectProps> = ({ id, defaultText, options, onSelect, selectedValue }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selected, setSelected] = useState(selectedValue || defaultText);

  const handleSelect = (option: CustomSelectOption) => {
    const optionLabel = typeof option === 'object' ? option.label : option;
    const optionValue = typeof option === 'object' ? option.value : option;
    
    setSelected(optionLabel);
    setIsOpen(false);
    if (onSelect) {
      onSelect(optionValue);
    }
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest(`#${id}`)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [id]);

  return (
    <div id={id} className="relative w-full">
      <div
        className={`flex items-center justify-between p-3 border-2 rounded-lg bg-white text-sm text-gray-700 cursor-pointer transition-all duration-200 hover:border-red-400 ${
          isOpen ? 'border-red-400' : 'border-gray-200'
        }`}
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="font-medium">{selected}</span>
        <ChevronDown 
          className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`} 
        />
      </div>
      
      {isOpen && (
        <div className="absolute top-full left-0 right-0 z-50 bg-white border-2 border-red-400 border-t-0 rounded-b-lg shadow-lg max-h-48 overflow-y-auto opacity-100 visible transform translate-y-0 transition-all duration-200">
          {options.map((option, index) => {
            const isObject = typeof option === 'object';
            const label = isObject ? option.label : option;
            const description = isObject ? option.description : null;
            
            return (
              <div
                key={index}
                className="p-3 cursor-pointer transition-colors duration-200 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
                onClick={() => handleSelect(option)}
              >
                <div className="font-semibold text-gray-900">{label}</div>
                {description && (
                  <div className="text-xs text-gray-600 mt-1">{description}</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// Topic Card Component
type Topic = {
  id: string;
  title: string;
  icon: string;
  description: string;
};

type TopicCardProps = {
  topic: Topic;
  isSelected: boolean;
  onSelect: (topic: Topic) => void;
};

const TopicCard: React.FC<TopicCardProps> = ({ topic, isSelected, onSelect }) => (
  <div
    className={`p-4 border-2 rounded-xl cursor-pointer transition-all duration-200 bg-white hover:border-red-400 hover:-translate-y-0.5 hover:shadow-lg ${
      isSelected ? 'border-red-400 bg-red-50' : 'border-gray-200'
    }`}
    onClick={() => onSelect(topic)}
  >
    <div className="flex items-center gap-3 mb-2">
      <span className="text-2xl">{topic.icon}</span>
      <span className="text-sm font-semibold text-gray-900">{topic.title}</span>
    </div>
    <div className="text-xs text-gray-600 leading-relaxed">{topic.description}</div>
  </div>
);

// Duration Card Component
type Duration = {
  value: string;
  label: string;
  description: string;
  wordCount: string;
  icon: string;
  recommended?: boolean;
};

type DurationCardProps = {
  duration: Duration;
  isSelected: boolean;
  onSelect: (duration: Duration) => void;
};

const DurationCard: React.FC<DurationCardProps> = ({ duration, isSelected, onSelect }) => (
  <div
    className={`p-4 border-2 rounded-xl cursor-pointer transition-all duration-200 bg-white relative hover:border-red-400 hover:-translate-y-0.5 ${
      isSelected ? 'border-red-400 bg-red-50' : 'border-gray-200'
    }`}
    onClick={() => onSelect(duration)}
  >
    {duration.recommended && (
      <div className="absolute -top-2 right-3 bg-red-400 text-white text-xs font-semibold px-2 py-1 rounded">
        Recommended
      </div>
    )}
    <div className="flex items-center gap-3 mb-2">
      <span className="text-xl">{duration.icon}</span>
      <span className="text-base font-semibold text-gray-900">{duration.label}</span>
    </div>
    <div className="text-xs text-gray-600 mb-1">{duration.description}</div>
    <div className="text-xs text-gray-600">{duration.wordCount}</div>
  </div>
);

// Main Training Wizard Component
type TrainingWizardProps = {
  isVisible: boolean;
  onClose: () => void;
  onGenerateContent: (config: any) => void;
};

type SelectionsState = {
  topic: string | null;
  customTopic: string;
  role: string | null;
  discipline: string | null;
  duration: string | null;
  objectives: string[];
};

const TrainingWizard: React.FC<TrainingWizardProps> = ({ isVisible, onClose, onGenerateContent }) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [selections, setSelections] = useState<SelectionsState>({
    topic: null,
    customTopic: '',
    role: null,
    discipline: null,
    duration: null,
    objectives: []
  });

  const totalSteps = 4;

  const topics = [
    { id: "wound-care", title: "Wound Care Assessment", icon: "🩹", description: "Assessment, documentation, and treatment" },
    { id: "fall-prevention", title: "Fall Prevention", icon: "🛡️", description: "Risk assessment and safety protocols" },
    { id: "medication-management", title: "Medication Management", icon: "💊", description: "Administration, reconciliation, and safety" },
    { id: "oasis-assessment", title: "OASIS Assessment", icon: "📋", description: "Completion, accuracy, and compliance" },
    { id: "infection-control", title: "Infection Control", icon: "🦠", description: "Prevention protocols and safety measures" },
    { id: "patient-safety", title: "Patient Safety", icon: "🔒", description: "Risk management and emergency response" },
    { id: "documentation", title: "Clinical Documentation", icon: "📝", description: "Requirements, accuracy, and compliance" },
    { id: "pain-management", title: "Pain Assessment & Management", icon: "⚡", description: "Evaluation, intervention, and monitoring" },
    { id: "diabetes-care", title: "Diabetes Management", icon: "🩸", description: "Monitoring, education, and complications" },
    { id: "cardiac-care", title: "Cardiac Care", icon: "❤️", description: "Heart failure, monitoring, and education" },
    { id: "respiratory-care", title: "Respiratory Care", icon: "🫁", description: "COPD, oxygen therapy, and breathing" },
    { id: "skin-integrity", title: "Skin & Pressure Injury", icon: "🔍", description: "Prevention, assessment, and treatment" },
    { id: "mental-health", title: "Mental Health Assessment", icon: "🧠", description: "Depression screening and support" },
    { id: "nutrition", title: "Nutritional Assessment", icon: "🥗", description: "Screening, education, and interventions" },
    { id: "mobility", title: "Mobility & Transfer", icon: "🚶", description: "Assessment, safety, and assistance" },
    { id: "communication", title: "Patient Communication", icon: "💬", description: "Therapeutic communication and education" },
    { id: "emergency-response", title: "Emergency Procedures", icon: "🚨", description: "Crisis management and response protocols" },
    { id: "discharge-planning", title: "Discharge Planning", icon: "🏠", description: "Transitions, coordination, and continuity" },
    { id: "family-education", title: "Family & Caregiver Education", icon: "👨‍👩‍👧‍👦", description: "Teaching and support strategies" },
    { id: "quality-measures", title: "Quality Improvement", icon: "📈", description: "CMS measures and performance improvement" },
    { id: "regulatory-compliance", title: "Regulatory Compliance", icon: "⚖️", description: "CoPs, state regulations, and surveys" },
    { id: "interdisciplinary-care", title: "Team Coordination", icon: "🤝", description: "Communication and care coordination" },
    { id: "post-hospitalization", title: "Post-Hospitalization Care", icon: "🏥", description: "Transition into home environment and syndrome management" },
    { id: "cultural-competency", title: "Cultural Competency", icon: "🌍", description: "Diverse populations and communication" },
    { id: "custom-topic", title: "Custom Topic", icon: "✏️", description: "Enter your own training subject" }
  ];

  const roles = [
    { value: "frontline-staff", label: "Frontline Staff", description: "Direct patient care providers" },
    { value: "clinical-manager", label: "Clinical Manager", description: "Supervisors and team leaders" },
    { value: "educator", label: "Educator", description: "Training coordinators and mentors" },
    { value: "director", label: "Director", description: "Senior leadership and administrators" }
  ];

  const disciplines = [
    { value: "rn", label: "RN - Registered Nurse", description: "Licensed nursing professionals" },
    { value: "lpn", label: "LPN - Licensed Practical Nurse", description: "Practical nursing professionals" },
    { value: "pt", label: "PT - Physical Therapist", description: "Physical therapy professionals" },
    { value: "pta", label: "PTA - Physical Therapist Assistant", description: "Physical therapy assistants" },
    { value: "ot", label: "OT - Occupational Therapist", description: "Occupational therapy professionals" },
    { value: "ota", label: "OTA - Occupational Therapist Assistant", description: "Occupational therapy assistants" },
    { value: "slp", label: "SLP - Speech-Language Pathologist", description: "Speech and language professionals" },
    { value: "msw", label: "MSW - Medical Social Worker", description: "Social work professionals" },
    { value: "hha", label: "HHA - Home Health Aide", description: "Home health aide professionals" }
  ];

  const durations = [
    { value: "5-minutes", label: "5 Minutes", description: "Quick, focused learning", wordCount: "~625-750 words", icon: "⚡" },
    { value: "10-minutes", label: "10 Minutes", description: "Comprehensive coverage", wordCount: "~1,250-1,500 words", icon: "📚", recommended: true },
    { value: "15-minutes", label: "15 Minutes", description: "In-depth exploration", wordCount: "~1,875-2,250 words", icon: "🎓" }
  ];

  // Reset wizard when it becomes visible
  useEffect(() => {
    if (isVisible) {
      setCurrentStep(1);
      setSelections({
        topic: null,
        customTopic: '',
        role: null,
        discipline: null,
        duration: null,
        objectives: []
      });
    }
  }, [isVisible]);

  const generateObjectives = () => {
    const objectiveTemplates = [
      [
        "Identify key assessment criteria and documentation requirements",
        "Demonstrate proper technique and safety protocols",
        "Apply evidence-based practices to patient care scenarios",
        "Recognize complications and implement appropriate interventions"
      ],
      [
        "Evaluate patient conditions using standardized assessment tools",
        "Implement appropriate interventions based on clinical findings",
        "Document care activities according to regulatory requirements",
        "Collaborate effectively with interdisciplinary team members"
      ],
      [
        "Analyze patient data to identify potential risks and complications",
        "Develop individualized care plans based on assessment findings",
        "Execute proper procedures following safety guidelines",
        "Monitor patient responses and adjust interventions accordingly"
      ]
    ];
    
    const randomIndex = Math.floor(Math.random() * objectiveTemplates.length);
    const objectives = objectiveTemplates[randomIndex];
    setSelections(prev => ({ ...prev, objectives }));
  };

interface ValidateStepFn {
    (step: number): boolean;
}

const validateStep: ValidateStepFn = (step) => {
    switch(step) {
        case 1:
            return selections.topic !== null && (selections.topic !== 'custom-topic' || selections.customTopic.trim().length > 0);
        case 2:
            return selections.role !== null && selections.discipline !== null;
        case 3:
            return selections.duration !== null;
        case 4:
            return selections.objectives.length > 0;
        default:
            return false;
    }
};

  const nextStep = () => {
    if (currentStep < totalSteps) {
      setCurrentStep(prev => prev + 1);
      if (currentStep === 3) {
        generateObjectives();
      }
    } else {
      handleGenerateContent();
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleGenerateContent = () => {
    const config = {
      topic: selections.topic === 'custom-topic' ? selections.customTopic : topics.find(t => t.id === selections.topic)?.title,
      role: roles.find(r => r.value === selections.role)?.label,
      discipline: disciplines.find(d => d.value === selections.discipline)?.label,
      duration: selections.duration,
      objectives: selections.objectives
    };
    
    onGenerateContent(config);
  };

  const progressWidth = (currentStep / totalSteps) * 100;
  const isStepValid = validateStep(currentStep);

  if (!isVisible) return null;

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Background overlay */}
      <div 
        className="flex-1 bg-black bg-opacity-50 flex items-center justify-center cursor-pointer" 
        onClick={onClose}
      >
        <div className="text-white text-center pointer-events-none">
          <div className="text-2xl font-bold mb-2">PDF Training Generator</div>
          <div className="text-lg opacity-90">Configure your training content using the wizard</div>
        </div>
      </div>
      
      {/* Training Wizard Sidebar */}
      <div className="w-96 h-screen bg-white shadow-2xl flex flex-col overflow-hidden">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-red-400 to-red-500 text-white p-6 pb-4 relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-8 h-8 bg-white bg-opacity-20 rounded-lg flex items-center justify-center hover:bg-opacity-30 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
          <div className="text-xl font-bold mb-1">PDF Training Generator</div>
          <div className="text-sm opacity-90">Create personalized healthcare training PDFs</div>
          <div className="mt-4 bg-white bg-opacity-20 h-1 rounded-full overflow-hidden">
            <div 
              className="bg-white h-full rounded-full transition-all duration-300"
              style={{ width: `${progressWidth}%` }}
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 p-6 overflow-y-auto">
          
          {/* Step 1: Topic Selection */}
          {currentStep === 1 && (
            <div>
              <div className="text-lg font-semibold text-gray-900 mb-2">Select Training Topic</div>
              <div className="text-sm text-gray-600 mb-6">What subject do you want to create training for?</div>
              
              <div className="grid grid-cols-1 gap-3 max-h-96 overflow-y-auto pr-2">
                {topics.map(topic => (
                  <TopicCard
                    key={topic.id}
                    topic={topic}
                    isSelected={selections.topic === topic.id}
                    onSelect={(topic) => setSelections(prev => ({ 
                      ...prev, 
                      topic: topic.id,
                      customTopic: topic.id === 'custom-topic' ? prev.customTopic : ''
                    }))}
                  />
                ))}
              </div>
              
              {selections.topic === 'custom-topic' && (
                <input
                  type="text"
                  className="w-full p-3 border-2 border-gray-200 rounded-lg text-sm mt-3 focus:border-red-400 focus:outline-none"
                  placeholder="Enter custom training topic..."
                  value={selections.customTopic}
                  onChange={(e) => setSelections(prev => ({ ...prev, customTopic: e.target.value }))}
                />
              )}
            </div>
          )}

          {/* Step 2: Audience Selection */}
          {currentStep === 2 && (
            <div>
              <div className="text-lg font-semibold text-gray-900 mb-2">Define Your Audience</div>
              <div className="text-sm text-gray-600 mb-6">Who will be taking this training?</div>
              
              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Role</label>
                  <CustomSelect
                    id="roleSelect"
                    defaultText="Select role..."
                    options={roles}
                    onSelect={(value) => setSelections(prev => ({ ...prev, role: value }))}
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-2">Discipline</label>
                  <CustomSelect
                    id="disciplineSelect"
                    defaultText="Select discipline..."
                    options={disciplines}
                    onSelect={(value) => setSelections(prev => ({ ...prev, discipline: value }))}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Duration Selection */}
          {currentStep === 3 && (
            <div>
              <div className="text-lg font-semibold text-gray-900 mb-2">Choose Training Duration</div>
              <div className="text-sm text-gray-600 mb-6">How long should this training be?</div>
              
              <div className="grid grid-cols-1 gap-3">
                {durations.map(duration => (
                  <DurationCard
                    key={duration.value}
                    duration={duration}
                    isSelected={selections.duration === duration.value}
                    onSelect={(duration) => setSelections(prev => ({ ...prev, duration: duration.value }))}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Step 4: Objectives Review */}
          {currentStep === 4 && (
            <div>
              <div className="text-lg font-semibold text-gray-900 mb-2">Review Learning Objectives</div>
              <div className="text-sm text-gray-600 mb-6">AI-generated learning objectives based on your selections</div>
              
              <div className="bg-gray-50 rounded-xl p-5 mb-5">
                <div className="text-base font-semibold text-gray-900 mb-4">After completing this training, learners will be able to:</div>
                <ul className="space-y-3 mb-4">
                  {selections.objectives.map((objective, index) => (
                    <li key={index} className="flex items-start gap-2 text-sm text-gray-700 leading-relaxed">
                      <span className="text-red-400 font-bold mt-0.5">•</span>
                      <span>{objective}</span>
                    </li>
                  ))}
                </ul>
                <button
                  onClick={generateObjectives}
                  className="bg-red-400 text-white px-4 py-2.5 rounded-lg text-xs font-semibold hover:bg-red-500 transition-colors"
                >
                  Generate Different Objectives
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="p-4 border-t border-gray-200 bg-gray-50 flex justify-between items-center">
          <button
            onClick={prevStep}
            className={`px-5 py-3 rounded-lg text-sm font-semibold transition-colors ${
              currentStep === 1 
                ? 'invisible' 
                : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
            }`}
          >
            Previous
          </button>
          
          <div className="text-xs text-gray-600">
            Step {currentStep} of {totalSteps}
          </div>
          
          <button
            onClick={nextStep}
            disabled={!isStepValid}
            className={`px-5 py-3 rounded-lg text-sm font-semibold transition-colors ${
              isStepValid
                ? 'bg-red-400 text-white hover:bg-red-500'
                : 'bg-gray-200 text-gray-400 cursor-not-allowed'
            }`}
          >
            {currentStep === totalSteps ? 'Generate PDF' : 'Next Step'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TrainingWizard;