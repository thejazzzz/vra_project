import { create } from "zustand";

interface UIState {
    previewPaperId: string | null;
    openPaperPreview: (id: string) => void;
    closePaperPreview: () => void;
}

export const useUIStore = create<UIState>((set) => ({
    previewPaperId: null,
    openPaperPreview: (id) => set({ previewPaperId: id }),
    closePaperPreview: () => set({ previewPaperId: null }),
}));
