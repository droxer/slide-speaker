import React, { createContext, useContext, useMemo, useState } from 'react';

type UIContextValue = {
  showTaskMonitor: boolean;
  setShowTaskMonitor: (v: boolean) => void;
};

const UIContext = createContext<UIContextValue | undefined>(undefined);

export const UIProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [showTaskMonitor, setShowTaskMonitor] = useState<boolean>(false);
  const value = useMemo(() => ({ showTaskMonitor, setShowTaskMonitor }), [showTaskMonitor]);
  return <UIContext.Provider value={value}>{children}</UIContext.Provider>;
};

export const useUI = (): UIContextValue => {
  const ctx = useContext(UIContext);
  if (!ctx) throw new Error('useUI must be used within a UIProvider');
  return ctx;
};

export default UIContext;

