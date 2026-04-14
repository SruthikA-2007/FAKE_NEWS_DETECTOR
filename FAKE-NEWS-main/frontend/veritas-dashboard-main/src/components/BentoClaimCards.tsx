import { motion } from "framer-motion";
import { AlertTriangle, CheckCircle2, HelpCircle } from "lucide-react";

type Claim = {
  text: string;
  confidence: number;
  verdict: string;
};

interface BentoClaimCardsProps {
  claims: Claim[];
}

const verdictConfig = {
  True: { icon: CheckCircle2, color: "text-emerald-400", border: "border-emerald-500/20" },
  False: { icon: AlertTriangle, color: "text-red-400", border: "border-red-500/20" },
  Unverified: { icon: HelpCircle, color: "text-amber-400", border: "border-amber-500/20" },
  Misleading: { icon: AlertTriangle, color: "text-orange-400", border: "border-orange-500/20" },
};

const BentoClaimCards = ({ claims }: BentoClaimCardsProps) => {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold tracking-tight text-foreground">Claim Analysis</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {claims.map((claim, i) => {
          const config = verdictConfig[claim.verdict as keyof typeof verdictConfig] ?? verdictConfig.Unverified;
          const Icon = config.icon;
          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1, duration: 0.3 }}
              whileHover={{ y: -5 }}
              className={`glass-hover p-4 space-y-3 cursor-default ${config.border}`}
            >
              <p className="text-sm text-foreground leading-relaxed line-clamp-2">{claim.text}</p>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <Icon className={`h-3.5 w-3.5 ${config.color}`} />
                  <span className={`text-xs font-medium ${config.color}`}>{claim.verdict}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 rounded-full bg-secondary overflow-hidden">
                    <motion.div
                      className="h-full rounded-full bg-primary"
                      initial={{ width: 0 }}
                      animate={{ width: `${claim.confidence}%` }}
                      transition={{ delay: i * 0.1 + 0.3, duration: 0.5 }}
                    />
                  </div>
                  <span className="text-xs text-muted-foreground">{claim.confidence}%</span>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};

export default BentoClaimCards;
