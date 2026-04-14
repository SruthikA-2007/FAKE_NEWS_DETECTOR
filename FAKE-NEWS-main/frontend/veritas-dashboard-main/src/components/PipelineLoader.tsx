import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Loader2 } from "lucide-react";

const stages = [
  "Extracting claims...",
  "Identifying entities...",
  "Cross-referencing sources...",
  "Running sentiment analysis...",
  "Verifying sources...",
  "Generating report...",
];

const PipelineLoader = () => {
  const [completed, setCompleted] = useState(-1);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    stages.forEach((_, i) => {
      timers.push(setTimeout(() => setCompleted(i), (i + 1) * 800));
    });
    return () => timers.forEach(clearTimeout);
  }, []);

  const progress = ((completed + 1) / stages.length) * 100;

  return (
    <div className="glass p-6 space-y-4">
      <h3 className="text-sm font-semibold tracking-tight text-foreground">Analysis Pipeline</h3>
      <div className="space-y-3">
        {stages.map((stage, i) => (
          <AnimatePresence key={i}>
            {i <= completed + 1 && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className="flex items-center gap-3 text-sm"
              >
                {i <= completed ? (
                  <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 300 }}>
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  </motion.div>
                ) : (
                  <Loader2 className="h-4 w-4 text-primary animate-spin" />
                )}
                <span className={i <= completed ? "text-muted-foreground" : "text-foreground"}>
                  {stage}
                </span>
              </motion.div>
            )}
          </AnimatePresence>
        ))}
      </div>
      <div className="h-1.5 rounded-full bg-secondary overflow-hidden">
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-rose-500 to-red-600"
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          style={{ boxShadow: "0 0 12px hsl(0 72% 51% / 0.5)" }}
        />
      </div>
    </div>
  );
};

export default PipelineLoader;
