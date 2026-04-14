import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

import { type Entity } from "@/services/api";

const entityColors: Record<Entity["type"], string> = {
  person: "bg-rose-900/60",
  date: "bg-red-900/50",
  money: "bg-amber-900/50",
  org: "bg-pink-900/50",
};

const entityLabels: Record<Entity["type"], string> = {
  person: "Person",
  date: "Date",
  money: "Money",
  org: "Organization",
};

interface EntityHighlighterProps {
  text?: string;
  entities?: Entity[];
}

const EntityHighlighter = ({ text = "", entities = [] }: EntityHighlighterProps) => {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setVisible(true); },
      { threshold: 0.3 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  const renderText = () => {
    if (!text) return null;
    let remaining = text;
    const parts: React.ReactNode[] = [];
    let key = 0;

    while (remaining.length > 0) {
      let earliest = -1;
      let matchedEntity: Entity | null = null;

      for (const entity of entities) {
        const idx = remaining.indexOf(entity.text);
        if (idx !== -1 && (earliest === -1 || idx < earliest)) {
          earliest = idx;
          matchedEntity = entity;
        }
      }

      if (matchedEntity && earliest !== -1) {
        if (earliest > 0) {
          parts.push(<span key={key++}>{remaining.slice(0, earliest)}</span>);
        }
        parts.push(
          <motion.span
            key={key++}
            className={`relative inline rounded px-1 py-0.5 ${entityColors[matchedEntity.type]}`}
            initial={{ backgroundSize: "0% 100%" }}
            animate={visible ? { backgroundSize: "100% 100%" } : {}}
            transition={{ duration: 0.6, delay: key * 0.08 }}
            title={entityLabels[matchedEntity.type]}
          >
            {matchedEntity.text}
          </motion.span>
        );
        remaining = remaining.slice(earliest + matchedEntity.text.length);
      } else {
        parts.push(<span key={key++}>{remaining}</span>);
        break;
      }
    }
    return parts;
  };

  return (
    <div ref={ref} className="glass p-6 space-y-4">
      <h3 className="text-sm font-semibold tracking-tight text-foreground">Entity Extraction</h3>
      <p className="text-sm leading-relaxed text-foreground/80">{renderText()}</p>
      <div className="flex flex-wrap gap-3 pt-2">
        {Object.entries(entityLabels).map(([type, label]) => (
          <div key={type} className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <div className={`h-2.5 w-2.5 rounded-sm ${entityColors[type as Entity["type"]]}`} />
            {label}
          </div>
        ))}
      </div>
    </div>
  );
};

export default EntityHighlighter;
