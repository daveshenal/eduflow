import React, { useMemo, useState } from 'react';
import Dropdown from './Dropdown';
import { DropdownOption } from '../types';

// Duration Card
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
    className={`p-4 mt-4 border-2 rounded-xl cursor-pointer transition-all duration-200 bg-white relative hover:border-red-400 ${isSelected ? 'border-red-400 bg-red-50' : 'border-gray-200'}`}
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

type TrainingWizardProps = {
  onGenerateContent?: (config: any) => void;
  onCancel?: () => void;
};

const roleOptions: DropdownOption[] = [
  { value: 'frontline-staff', label: 'Frontline Staff', active: true },
  { value: 'clinical-manager', label: 'Clinical Manager' },
  { value: 'educator', label: 'Educator' },
  { value: 'director', label: 'Director' },
];

const disciplineOptions: DropdownOption[] = [
  { value: 'rn', label: 'RN - Registered Nurse', active: true },
  { value: 'lpn', label: 'LPN - Licensed Practical Nurse' },
  { value: 'pt', label: 'PT - Physical Therapist' },
  { value: 'pta', label: 'PTA - Physical Therapist Assistant' },
  { value: 'ot', label: 'OT - Occupational Therapist' },
  { value: 'ota', label: 'OTA - Occupational Therapist Assistant' },
  { value: 'slp', label: 'SLP - Speech-Language Pathologist' },
  { value: 'msw', label: 'MSW - Medical Social Worker' },
  { value: 'hha', label: 'HHA - Home Health Aide' },
];

const durations: Duration[] = [
  { value: '5-minutes', label: '5 Minutes', description: 'Quick, focused learning', wordCount: '~625-750 words', icon: '⚡' },
  { value: '10-minutes', label: '10 Minutes', description: 'Comprehensive coverage', wordCount: '~1,250-1,500 words', icon: '📚', recommended: true },
];

const TrainingWizard: React.FC<TrainingWizardProps> = ({ onGenerateContent, onCancel }) => {
  const [currentStep, setCurrentStep] = useState<number>(1);
  const totalSteps = 3;

  const [learningFocus, setLearningFocus] = useState<string>('');
  const [specificTopic, setSpecificTopic] = useState<string>('');
  const [clinicalContext, setClinicalContext] = useState<string>(
    `Post-hospitalization patients - Patients recently discharged from hospital\nHigh-risk for readmission - Patients with multiple risk factors\nComplex chronic conditions - Multiple comorbidities and ongoing management`
  );
  const [role, setRole] = useState<string>('');
  const [discipline, setDiscipline] = useState<string>('');
  const [expectedOutcomes, setExpectedOutcomes] = useState<string>(
    `Identify key assessment criteria and documentation requirements\nDemonstrate proper technique and safety protocols\nApply evidence-based practices to patient care scenarios\nRecognize complications and implement appropriate interventions`
  );
  const [duration, setDuration] = useState<string>('');
  const [learningLevel, setLearningLevel] = useState<string>('');
  const [numHuddles, setNumHuddles] = useState<number | null>(null);

  const [learningLevelTouched, setLearningLevelTouched] = useState(true);

  // Per-step validation
  const stepValid = useMemo(() => {
    switch (currentStep) {
      case 1:
        return (
          learningFocus.trim().length > 0 &&
          specificTopic.trim().length > 0 &&
          clinicalContext.trim().length > 0
        );
      case 2:
        return (
          role.trim().length > 0 &&
          discipline.trim().length > 0 &&
          expectedOutcomes.trim().length > 0 &&
          learningLevelTouched
        );
      case 3:
        return duration.trim().length > 0 && numHuddles !== null && numHuddles >= 1 && numHuddles <= 10;
      default:
        return false;
    }
  }, [currentStep, learningFocus, specificTopic, clinicalContext, role, discipline, expectedOutcomes, duration, numHuddles]);

  // Progress by number of inputs completed (8 total)
  const completedInputs = useMemo(() => {
    let count = 0;
    if (learningFocus.trim()) count++;
    if (specificTopic.trim()) count++;
    if (clinicalContext.trim()) count++;
    if (role.trim()) count++;
    if (discipline.trim()) count++;
    if (expectedOutcomes.trim()) count++;
    if (duration.trim()) count++;
    if (learningLevel.trim()) count++;
    return count;
  }, [learningFocus, specificTopic, clinicalContext, role, discipline, expectedOutcomes, duration, learningLevel]);

  const progressWidth = (completedInputs / 8) * 100;

  const handleNext = () => {
    if (!stepValid) return;
    if (currentStep < totalSteps) {
      setCurrentStep(prev => prev + 1);
    } else {
      const roleLabel = roleOptions.find(r => r.value === role)?.label || role;
      const disciplineLabel = disciplineOptions.find(d => d.value === discipline)?.label || discipline;
      const config = {
        learningFocus,
        topic: specificTopic,
        clinicalContext,
        expectedOutcomes,
        role: roleLabel,
        roleValue: role,
        discipline: disciplineLabel,
        disciplineValue: discipline,
        duration,
        learningLevel,
        numHuddles,
      };
      // For now, log all inputs; later this will be sent to API
      console.log('Generate Huddle inputs:', config);
      onGenerateContent?.(config);
    }
  };

  const handlePrev = () => {
    if (currentStep > 1) setCurrentStep(prev => prev - 1);
  };

  return (
    <div className="huddles">
      <div className="huddles-body flex flex-col min-h-screen" style={{ flex: 1, overflowY: 'auto' }}>
        {currentStep === 1 && (
          <div className="huddle-inputs-1 mr-20">
            {/* Learning Focus */}
            <div className='config-section'>
              <div className="huddle-section-title">Learning Focus</div>
              <div className="config-group">
                <p className="huddle-label">What specific skill or knowledge should learners gain?</p>
                <input
                  type="text"
                  className="config-input"
                  id="learningFocus"
                  placeholder={'Clinical Assessment - Patient evaluation and monitoring skills'}
                  value={learningFocus}
                  onChange={(e) => setLearningFocus(e.target.value)}
                />
              </div>
            </div>

            {/* Specific Topic */}
            <div className='config-section'>
              <div className="huddle-section-title">Specific Topic</div>
              <div className="config-group">
                <p className="huddle-label">What is the main subject for this training?</p>
                <input
                  type="text"
                  className="config-input"
                  id="specificTopic"
                  placeholder={'Comprehensive nursing assessment techniques'}
                  value={specificTopic}
                  onChange={(e) => setSpecificTopic(e.target.value)}
                />
              </div>
            </div>

            {/* Clinical Context */}
            <div className='config-section'>
              <div className="huddle-section-title">Clinical Context</div>
              <div className="form-group">
                <p className="huddle-label">What specific patient scenario or situation should be emphasized?</p>
                <textarea
                  className="config-input"
                  id="clinicalContext"
                  placeholder={`Post-hospitalization patients - Patients recently discharged from hospital\nHigh-risk for readmission - Patients with multiple risk factors\nComplex chronic conditions - Multiple comorbidities and ongoing management`}
                  style={{ height: '120px', resize: 'none' }}
                  value={clinicalContext}
                  onChange={(e) => setClinicalContext(e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        {currentStep === 2 && (
          <div className="huddle-inputs-1 mr-20">
            <div className="config-section">
              <div className="huddle-section-title">Define Your Audience - Who will be taking this training?</div>
              <div className="form-row" style={{ display: 'flex', gap: '1rem' }}>
                <div className="config-group" style={{ flex: 1, width: '30%' }}>
                  <p className="huddle-label">Select Role</p>
                  <Dropdown
                    options={roleOptions}
                    value={role}
                    onChange={setRole}
                    placeholder="Select role"
                  />
                </div>
                <div className="config-group" style={{ flex: 1, width: '30%' }}>
                  <p className="huddle-label">Select Discipline</p>
                  <Dropdown
                    options={disciplineOptions}
                    value={discipline}
                    onChange={setDiscipline}
                    placeholder="Select discipline"
                  />
                </div>
              </div>

              {/* Learning Level */}
              <div className="config-group mt-4">
                <p className="huddle-label">Learning Level</p>
                <div className="flex gap-6 mb-2">
                  {['Introductory', 'Intermediate', 'Advanced'].map((level) => (
                    <label key={level} className="inline-flex items-center gap-2 text-sm text-gray-700">
                      <input
                        type="radio"
                        name="learning-level"
                        className="form-radio h-4 w-4 text-red-400 focus:ring-red-400"
                        checked={learningLevel === level}
                        onChange={() => {
                          setLearningLevel(level);
                          setLearningLevelTouched(true);
                        }}
                      />
                      <span>{level}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            {/* Expected Learning Outcomes */}
            <div className='config-section'>
              <div className="huddle-section-title">Expected Learning Outcomes</div>
              <div className="form-group">
                <p className="huddle-label">After this training, staff should be able to:</p>
                <textarea
                  className="config-input"
                  id="expectedOutcomes"
                  placeholder={`Identify key assessment criteria and documentation requirements\nDemonstrate proper technique and safety protocols\nApply evidence-based practices to patient care scenarios\nRecognize complications and implement appropriate interventions`}
                  style={{ height: '120px', resize: 'none' }}
                  value={expectedOutcomes}
                  onChange={(e) => setExpectedOutcomes(e.target.value)}
                />
              </div>
            </div>
          </div>
        )}

        {currentStep === 3 && (
          <div className="huddle-inputs-1 mr-20">
            <div className="config-section">
              <div className="huddle-section-title">Choose Training Duration</div>
              <div className="huddle-label">How long should this training be?</div>
              <div className="grid grid-cols-3 gap-3">
                {durations.map((d) => (
                  <DurationCard
                    key={d.value}
                    duration={d}
                    isSelected={duration === d.value}
                    onSelect={(dur) => setDuration(dur.value)}
                  />
                ))}
              </div>
              <div className="config-group mt-6">
                <div className="huddle-section-title">Number of Huddles</div>
                <div className="huddle-label">Select how many huddles to generate (1–10)</div>
                <div className='w-1/6'>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    className="config-input mt-2 w-24"
                    value={numHuddles ?? ''}
                    onChange={(e) => {
                      const val = parseInt(e.target.value || '', 10);
                      if (Number.isNaN(val)) {
                        setNumHuddles(null);
                      } else {
                        setNumHuddles(Math.max(1, Math.min(10, val)));
                      }
                    }}
                  />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {onCancel && (
        <div className="flex justify-end px-4 py-3">
          <button
            className="px-5 py-3 rounded-lg text-sm font-semibold transition-colors bg-gray-100 text-gray-700 hover:bg-gray-200"
            onClick={onCancel}
          >
            Back
          </button>
        </div>
      )}

      {/* Sticky Footer */}
      <div className="main-footer border-t border-gray-300 bg-white sticky bottom-0">
        <div className=" bg-white bg-opacity-20 h-1.5 overflow-hidden">
          <div
            className="bg-red-300 h-full rounded-r transition-all duration-300"
            style={{ width: `${progressWidth}%` }}
          />
        </div>
        <div className="flex justify-center items-center space-x-10 mt-4">
          <div className="flex items-center space-x-3">
            <button className="px-5 py-3 rounded-lg text-sm font-semibold transition-colors" onClick={handlePrev} disabled={currentStep === 1}>
              Previous
            </button>
          </div>
          <div className="text-xs text-gray-600">Step {currentStep} of {totalSteps}</div>
          <button
            className={`px-4 py-3 w-32 rounded-lg text-sm font-semibold transition-colors ${stepValid ? 'bg-red-400 text-white hover:bg-red-500' : 'bg-gray-200 text-gray-400 cursor-not-allowed'}`}
            onClick={handleNext}
            disabled={!stepValid}
          >
            {currentStep === totalSteps ? 'Generate' : 'Next Step'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TrainingWizard;