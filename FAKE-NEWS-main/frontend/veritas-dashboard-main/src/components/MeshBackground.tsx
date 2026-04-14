import { motion } from "framer-motion";

const MeshBackground = () => {
  return (
    <div className="fixed inset-0 -z-10 overflow-hidden bg-background">
      <motion.div
        className="absolute w-[600px] h-[600px] rounded-full opacity-20 blur-[120px]"
        style={{ background: "radial-gradient(circle, hsl(0 72% 40%), transparent)" }}
        animate={{
          x: ["-10%", "15%", "-5%"],
          y: ["-10%", "10%", "-15%"],
        }}
        transition={{ duration: 20, repeat: Infinity, repeatType: "reverse", ease: "easeInOut" }}
      />
      <motion.div
        className="absolute right-0 bottom-0 w-[500px] h-[500px] rounded-full opacity-10 blur-[100px]"
        style={{ background: "radial-gradient(circle, hsl(0 50% 30%), transparent)" }}
        animate={{
          x: ["10%", "-15%", "5%"],
          y: ["10%", "-10%", "15%"],
        }}
        transition={{ duration: 25, repeat: Infinity, repeatType: "reverse", ease: "easeInOut" }}
      />
      <motion.div
        className="absolute left-1/2 top-1/2 w-[400px] h-[400px] rounded-full opacity-[0.07] blur-[80px]"
        style={{ background: "radial-gradient(circle, hsl(350 60% 35%), transparent)" }}
        animate={{
          x: ["-50%", "-30%", "-60%"],
          y: ["-50%", "-30%", "-60%"],
        }}
        transition={{ duration: 18, repeat: Infinity, repeatType: "reverse", ease: "easeInOut" }}
      />
    </div>
  );
};

export default MeshBackground;
