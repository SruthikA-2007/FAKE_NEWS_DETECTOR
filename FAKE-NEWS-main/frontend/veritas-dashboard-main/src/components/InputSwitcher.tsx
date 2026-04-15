import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Link, Image, Upload, Search } from "lucide-react";

const tabs = [
  { id: "text", label: "Text", icon: FileText },
  { id: "url", label: "URL", icon: Link },
  { id: "image", label: "Image", icon: Image },
] as const;

type TabId = (typeof tabs)[number]["id"];

interface InputSwitcherProps {
  onAnalyze: (payload: { type: TabId; contentOrFile: string | File }) => void;
}

const InputSwitcher = ({ onAnalyze }: InputSwitcherProps) => {
  const [active, setActive] = useState<TabId>("text");
  const [textValue, setTextValue] = useState("");
  const [urlValue, setUrlValue] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [imagePreview, setImagePreview] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      if (imagePreview) {
        URL.revokeObjectURL(imagePreview);
      }
    };
  }, [imagePreview]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file?.type.startsWith("image/")) {
      setSelectedFile(file);
      setImagePreview(URL.createObjectURL(file));
    }
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file?.type.startsWith("image/")) {
      setSelectedFile(file);
      setImagePreview(URL.createObjectURL(file));
    }
  }, []);

  const handleAnalyze = useCallback(() => {
    if (active === "text") {
      const content = textValue.trim();
      if (!content) {
        return;
      }
      onAnalyze({ type: "text", contentOrFile: content });
      return;
    }

    if (active === "url") {
      const content = urlValue.trim();
      if (!content) {
        return;
      }
      onAnalyze({ type: "url", contentOrFile: content });
      return;
    }

    if (selectedFile) {
      onAnalyze({ type: "image", contentOrFile: selectedFile });
    }
  }, [active, onAnalyze, selectedFile, textValue, urlValue]);

  const isAnalyzeDisabled =
    (active === "text" && !textValue.trim()) ||
    (active === "url" && !urlValue.trim()) ||
    (active === "image" && !selectedFile);

  return (
    <div className="glass p-6 space-y-5">
      {/* Segmented Control */}
      <div className="relative flex gap-1 rounded-lg bg-secondary p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActive(tab.id)}
            className="relative z-10 flex flex-1 items-center justify-center gap-2 rounded-md px-4 py-2.5 text-sm font-medium transition-colors"
            style={{ color: active === tab.id ? "hsl(0 0% 100%)" : "hsl(215 15% 55%)" }}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
            {active === tab.id && (
              <motion.div
                layoutId="active-tab"
                className="absolute inset-0 rounded-md bg-primary"
                style={{ zIndex: -1 }}
                transition={{ type: "spring", stiffness: 400, damping: 30 }}
              />
            )}
          </button>
        ))}
      </div>

      {/* Input Views */}
      <AnimatePresence mode="wait">
        <motion.div
          key={active}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.2 }}
        >
          {active === "text" && (
            <textarea
              value={textValue}
              onChange={(e) => setTextValue(e.target.value)}
              className="w-full h-32 bg-secondary/50 rounded-lg p-4 text-sm text-foreground placeholder:text-muted-foreground border border-border focus:border-primary focus:outline-none resize-none leading-relaxed"
              placeholder="Paste an article or claim to analyze..."
            />
          )}
          {active === "url" && (
            <div className="flex gap-3">
              <input
                type="url"
                value={urlValue}
                onChange={(e) => setUrlValue(e.target.value)}
                className="flex-1 bg-secondary/50 rounded-lg px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground border border-border focus:border-primary focus:outline-none"
                placeholder="https://example.com/article"
              />
            </div>
          )}
          {active === "image" && (
            <motion.div
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              animate={dragOver ? { boxShadow: "0 0 30px hsl(0 72% 51% / 0.3)" } : { boxShadow: "0 0 0px transparent" }}
              className="flex flex-col items-center justify-center h-32 rounded-lg border-2 border-dashed border-border bg-secondary/30 cursor-pointer transition-colors hover:border-primary/50"
            >
              {imagePreview ? (
                <img src={imagePreview} alt="Preview" className="h-full object-contain rounded-lg" />
              ) : (
                <label className="flex flex-col items-center justify-center w-full h-full cursor-pointer">
                  <Upload className="h-8 w-8 text-muted-foreground mb-2" />
                  <p className="text-sm text-muted-foreground">Drop image or click to upload</p>
                  <input type="file" accept="image/*" onChange={handleFileChange} className="hidden" />
                </label>
              )}
            </motion.div>
          )}
        </motion.div>
      </AnimatePresence>

      <button
        onClick={handleAnalyze}
        disabled={isAnalyzeDisabled}
        className="w-full flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-3 text-sm font-semibold text-primary-foreground transition-all hover:bg-primary/90 hover:shadow-[0_0_20px_hsl(0_72%_51%/0.3)]"
      >
        <Search className="h-4 w-4" />
        Analyze Content
      </button>
    </div>
  );
};

export default InputSwitcher;
