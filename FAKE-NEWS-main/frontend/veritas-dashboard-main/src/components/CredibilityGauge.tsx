import { motion } from "framer-motion";

interface CredibilityGaugeProps {
  score: number; // 0-100
}

const CredibilityGauge = ({ score }: CredibilityGaugeProps) => {
  const radius = 90;
  const strokeWidth = 12;
  const cx = 120;
  const cy = 110;
  const startAngle = Math.PI;
  const endAngle = 0;
  const totalArc = Math.PI;
  const circumference = totalArc * radius;
  const scoreAngle = startAngle - (score / 100) * totalArc;

  const arcPath = (angle: number) => {
    const x = cx + radius * Math.cos(angle);
    const y = cy - radius * Math.sin(angle);
    return { x, y };
  };

  const start = arcPath(startAngle);
  const end = arcPath(endAngle);

  const needleEnd = arcPath(scoreAngle);

  const label = score < 35 ? "False" : score < 65 ? "Unverified" : "True";
  const labelColor = score < 30 ? "text-red-400" : score < 60 ? "text-amber-400" : "text-emerald-400";

  return (
    <div className="glass p-6 flex flex-col items-center">
      <h3 className="text-sm font-semibold tracking-tight text-foreground mb-4">Credibility Score</h3>
      <svg viewBox="0 0 240 140" className="w-full max-w-[280px]">
        {/* Background arc */}
        <path
          d={`M ${start.x} ${start.y} A ${radius} ${radius} 0 0 1 ${end.x} ${end.y}`}
          fill="none"
          stroke="hsl(0 0% 16%)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Score arc */}
        <motion.path
          d={`M ${start.x} ${start.y} A ${radius} ${radius} 0 0 1 ${end.x} ${end.y}`}
          fill="none"
          stroke="url(#gaugeGradient)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - (score / 100) * circumference }}
          transition={{ type: "spring", stiffness: 60, damping: 20, delay: 0.3 }}
        />
        {/* Needle */}
        <motion.line
          x1={cx}
          y1={cy}
          initial={{ x2: start.x, y2: start.y }}
          animate={{ x2: needleEnd.x, y2: needleEnd.y }}
          transition={{ type: "spring", stiffness: 60, damping: 20, delay: 0.3 }}
          stroke="hsl(0 0% 88%)"
          strokeWidth={2.5}
          strokeLinecap="round"
        />
        <circle cx={cx} cy={cy} r={4} fill="hsl(0 72% 51%)" />
        <defs>
          <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="hsl(0 72% 51%)" />
            <stop offset="50%" stopColor="hsl(40 90% 55%)" />
            <stop offset="100%" stopColor="hsl(140 60% 45%)" />
          </linearGradient>
        </defs>
      </svg>
      <motion.div
        className="text-center -mt-2"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.2 }}
      >
        <span className="text-4xl font-bold tracking-tight text-foreground">{score}</span>
        <span className="text-lg text-muted-foreground">/100</span>
        <p className={`text-sm font-medium mt-1 ${labelColor}`}>{label}</p>
      </motion.div>
    </div>
  );
};

export default CredibilityGauge;
