import React, { useState, useEffect, useRef, useCallback } from 'react';

// Type definitions
export interface MenuItem {
  id?: string | number;
  label?: string;
  name?: string;
  title?: string;
  text?: string;
  [key: string]: any;
}

export interface ScrollableMenuProps {
  items: (string | MenuItem)[];
  height?: string;
  onSelect?: (item: string | MenuItem, index: number) => void;
  emptyMessage?: string;
  placeholder?: string;
  className?: {
    container?: string;
    searchInput?: string;
    scrollArea?: string;
    list?: string;
    item?: string;
    itemDefault?: string;
    itemSelected?: string;
    emptyState?: string;
  };
}

const ScrollableMenu: React.FC<ScrollableMenuProps> = ({
  items,
  height = '256px',
  onSelect,
  emptyMessage = 'No items found',
  placeholder = 'Search items...',
  className = {}
}) => {
  // Default class names
  const defaultClassNames = {
    container: 'border border-gray-300 rounded-lg bg-white shadow-sm',
    searchInput: 'w-full p-3 border-b border-gray-300 focus:outline-none focus:border-blue-500',
    scrollArea: 'overflow-y-auto p-2',
    list: 'space-y-1',
    item: 'p-3 rounded cursor-pointer',
    itemDefault: 'hover:bg-gray-100',
    itemSelected: 'bg-blue-100',
    emptyState: 'text-gray-500 text-center py-8'
  };

  const classes = { ...defaultClassNames, ...className };

  // State
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [filteredItems, setFilteredItems] = useState<(string | MenuItem)[]>(items);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [displayValue, setDisplayValue] = useState<string>('');

  // Refs
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Helper function to get item content
  const getItemContent = (item: string | MenuItem): string => {
    if (typeof item === 'string') {
      return item;
    } else if (typeof item === 'object' && item !== null) {
      return item.label || item.name || item.title || item.text || JSON.stringify(item);
    }
    return String(item);
  };

  // Update filtered items when items or search query changes
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredItems(items);
    } else {
      const lowerQuery = searchQuery.toLowerCase();
      const filtered = items.filter(item => {
        const content = getItemContent(item).toLowerCase();
        return content.includes(lowerQuery);
      });
      setFilteredItems(filtered);
    }
  }, [items, searchQuery]);

  // Handle item selection
  const handleSelectItem = useCallback((index: number) => {
    if (index < 0 || index >= items.length) return;

    setSelectedIndex(index);
    const selectedItem = items[index];
    const itemContent = getItemContent(selectedItem);
    
    // Set display value to show selected item
    setDisplayValue(itemContent);
    setSearchQuery(''); // Clear search query to show all items

    // Trigger callback
    if (onSelect) {
      onSelect(selectedItem, index);
    }
  }, [items, onSelect]);

  // Handle search input change
  const handleSearchChange = (value: string) => {
    setDisplayValue(value);
    setSearchQuery(value);
    
    // Clear selection when typing
    if (value !== getItemContent(items[selectedIndex || -1])) {
      setSelectedIndex(null);
    }
  };

  // Handle keyboard navigation
  const handleKeyNavigation = (e: React.KeyboardEvent) => {
    const visibleItems = filteredItems;
    if (visibleItems.length === 0) return;

    let currentIndex = -1;
    if (selectedIndex !== null) {
      currentIndex = visibleItems.findIndex(item => items.indexOf(item) === selectedIndex);
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        const nextIndex = currentIndex + 1 < visibleItems.length ? currentIndex + 1 : 0;
        const nextOriginalIndex = items.indexOf(visibleItems[nextIndex]);
        handleSelectItem(nextOriginalIndex);
        break;
        
      case 'ArrowUp':
        e.preventDefault();
        const prevIndex = currentIndex > 0 ? currentIndex - 1 : visibleItems.length - 1;
        const prevOriginalIndex = items.indexOf(visibleItems[prevIndex]);
        handleSelectItem(prevOriginalIndex);
        break;
        
      case 'Enter':
        e.preventDefault();
        if (currentIndex >= 0) {
          const selectedOriginalIndex = items.indexOf(visibleItems[currentIndex]);
          if (onSelect) {
            onSelect(items[selectedOriginalIndex], selectedOriginalIndex);
          }
        }
        break;
        
      case 'Escape':
        e.preventDefault();
        setDisplayValue('');
        setSearchQuery('');
        setSelectedIndex(null);
        break;
    }
  };

  // Render items
  const renderItems = () => {
    if (filteredItems.length === 0) {
      return (
        <li className={classes.emptyState}>
          {emptyMessage}
        </li>
      );
    }

    return filteredItems.map((item, filteredIndex) => {
      const originalIndex = items.indexOf(item);
      const isSelected = selectedIndex === originalIndex;
      
      const itemClasses = [
        classes.item,
        isSelected ? classes.itemSelected : classes.itemDefault
      ].filter(Boolean).join(' ');

      return (
        <li
          key={`${originalIndex}-${filteredIndex}`}
          className={itemClasses}
          onClick={() => handleSelectItem(originalIndex)}
        >
          {getItemContent(item)}
        </li>
      );
    });
  };

  return (
    <div 
      className={classes.container}
      style={{ height, display: 'flex', flexDirection: 'column' }}
    >
      <input
        ref={searchInputRef}
        type="text"
        className={classes.searchInput}
        placeholder={placeholder}
        value={displayValue}
        onChange={(e) => handleSearchChange(e.target.value)}
        onKeyDown={handleKeyNavigation}
      />
      
      <div 
        ref={scrollAreaRef}
        className={classes.scrollArea}
        style={{ flex: 1 }}
      >
        <ul className={classes.list}>
          {renderItems()}
        </ul>
      </div>
    </div>
  );
};

export default ScrollableMenu;