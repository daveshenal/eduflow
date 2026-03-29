import React, { useState, useRef, useEffect } from 'react';
import { DropdownOption } from '../types';

interface DropdownProps<T = string> {
  options: DropdownOption[];
  value: T;
  onChange: (value: T) => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

const Dropdown = <T extends string>({
  options,
  value,
  onChange,
  placeholder = 'Select an option',
  disabled = false,
  className = 'dropdown',
}: DropdownProps<T>) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find(option => option.value === value);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleToggle = () => {
    if (!disabled) {
      setIsOpen(!isOpen);
    }
  };

  const handleOptionClick = (optionValue: string) => {
    onChange(optionValue as T);
    setIsOpen(false);
  };

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <div className="relative">
        <div
          className={`
            flex items-center justify-between w-full px-3 py-3 text-left
            bg-white border border-gray-300 rounded-t-lg shadow-sm
            ${disabled 
              ? 'opacity-50 cursor-not-allowed bg-gray-50' 
              : 'cursor-pointer hover:border-gray-400'
            }
            ${isOpen ? 'border-gray-400' : ''}
          `}
          style={isOpen ? { borderColor: '#40798c' } : {}}
          onClick={handleToggle}
        >
          <span className="block truncate text-gray-900">
            {selectedOption ? selectedOption.label : placeholder}
          </span>
          <svg
            className={`w-4 h-4 text-gray-500 transform transition-transform duration-200 ${
              isOpen ? 'rotate-180' : ''
            }`}
            width="16"
            height="16"
            viewBox="0 0 20 20"
            fill="none"
          >
            <path
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.5"
              d="M6 8l4 4 4-4"
            />
          </svg>
        </div>
        
        {isOpen && (
          <div className="absolute z-10 w-full bg-white border border-gray-300 rounded-b-lg shadow-lg overflow-hidden">
            <div 
              className="pt-3"
              style={{
                maxHeight: `${5 * 40 + 12}px`, // 3 items * 40px + 12px top padding
                overflowY: options.length > 3 ? 'auto' : 'visible'
              }}
            >
              {options.map((option) => (
                <div
                  key={option.value}
                  className={`
                    px-3 py-2 text-gray-900 cursor-pointer select-none
                    ${option.value === value ? 'text-white font-medium' : ''}
                    ${option.active ? 'bg-gray-50' : ''}
                  `}
                  style={{ 
                    minHeight: '40px', 
                    display: 'flex', 
                    alignItems: 'center',
                    backgroundColor: option.value === value ? '#40798c' : undefined
                  }}
                  onMouseEnter={(e) => {
                    if (option.value !== value) {
                      e.currentTarget.style.backgroundColor = 'rgba(64, 121, 140, 0.1)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (option.value !== value) {
                      e.currentTarget.style.backgroundColor = '';
                    }
                  }}
                  onClick={() => handleOptionClick(option.value)}
                >
                  {option.label}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dropdown;