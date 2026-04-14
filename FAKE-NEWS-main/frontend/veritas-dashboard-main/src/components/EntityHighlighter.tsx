import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";

interface Entity {
  text: string;
  type: "person" | "date" | "money" | "org";
}

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

const sampleText = `According to Dr. James Whitfield, the study conducted on January 15, 2024 by the International Coffee Cartel revealed that a $2.4 million investment led to the discovery. Lead researcher Maria Santos confirmed that the 12 participants each received $500 for their weekend-long participation. The findings were later disputed by the World Health Organization on February 3, 2024.`;

const entities: Entity[] = [
  { text: "Dr. James Whitfield", type: "person" },
  { text: "January 15, 2024", type: "date" },
  { text: "International Coffee Cartel", type: "org" },
  { text: "$2.4 million", type: "money" },
  { text: "Maria Santos", type: "person" },
  { text: "$500", type: "money" },
  { text: "World Health Organization", type: "org" },
  { text: "February 3, 2024", type: "date" },
];

const EntityHighlighter = () => {
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
    let remaining = sampleText;
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
