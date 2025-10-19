import { useEffect, useRef } from 'react';

/**
 * A hook that traps focus within a container element
 * @param isActive - Whether the focus trap is active
 */
export const useFocusTrap = (isActive: boolean) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    const container = containerRef.current;
    let focusableElements: HTMLElement[] = [];
    const previouslyFocusedElement = document.activeElement as HTMLElement;

    const getFocusableElements = () => {
      return Array.from(
        container.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
      ).filter((el) => {
        return !el.hasAttribute('disabled') && !el.getAttribute('aria-hidden');
      });
    };

    const handleFocusIn = () => {
      // Update focusable elements in case they change
      focusableElements = getFocusableElements();
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;

      focusableElements = getFocusableElements();

      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (event.shiftKey) {
        // Shift + Tab
        if (document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab
        if (document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    };

    // Initialize focus trap
    focusableElements = getFocusableElements();

    if (focusableElements.length > 0) {
      // Focus the first element
      focusableElements[0].focus();
    }

    // Add event listeners
    container.addEventListener('focusin', handleFocusIn);
    container.addEventListener('keydown', handleKeyDown);

    return () => {
      // Remove event listeners
      container.removeEventListener('focusin', handleFocusIn);
      container.removeEventListener('keydown', handleKeyDown);

      // Restore focus to the previously focused element
      if (previouslyFocusedElement && previouslyFocusedElement.focus) {
        previouslyFocusedElement.focus();
      }
    };
  }, [isActive]);

  return containerRef;
};