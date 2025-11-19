import { useState, useEffect, useRef } from "react";
import { useNavigate } from 'react-router-dom';
import Button from "../components/ui/Button";
import { PostService } from "../scripts/post-service";
import ProgressBar from "../components/ui/ProgressBar";
import Container from "../components/layout/Container";

const BreathingPracticePage = () => {
   const navigate = useNavigate();
   const [text, setText] = useState("0 с");
   const [value, setValue] = useState(0);
   const [title, setTitle] = useState("Вдыхайте...");
   const [phase, setPhase] = useState("inhale"); 
   const [times, setTimes] = useState(0); 
   
   const timerRef = useRef(null);
   const secondsRef = useRef(0);
   const timesRef = useRef(0);

   const breathingPhases = {
      inhale: { duration: 4, next: "hold", title: "Вдыхайте..." },
      hold: { duration: 7, next: "exhale", title: "Задержите дыхание" },
      exhale: { duration: 8, next: "rest", title: "Медленно выдыхайте..." },
      rest: { duration: 5, next: "inhale", title: "" }
   };

   const startBreathingCycle = () => {
      secondsRef.current = 0; 
      setValue(0); 
      setText("0 с");
      setTitle(breathingPhases[phase].title);
   };

   const stopBreathingCycle = () => {
      if (timerRef.current) {
         clearInterval(timerRef.current);
         timerRef.current = null;
      }
   };

   useEffect(() => {
      const currentPhase = breathingPhases[phase];
      const totalSeconds = currentPhase.duration;

      timerRef.current = setInterval(() => {
         secondsRef.current += 1;
         const progress = (secondsRef.current / totalSeconds) * 100;
         setValue(progress);
         setText(`${secondsRef.current} с`);
         if (phase === "rest") {
            setTitle(`Упражнение выполнено ${timesRef.current + 1} из 5 раз`);
         } else {
            setTitle(currentPhase.title);
         };
         if (secondsRef.current >= totalSeconds) {
            clearInterval(timerRef.current);
            const nextPhase = currentPhase.next;
            if (phase === "rest") {
               const newTimes = timesRef.current + 1;
               timesRef.current = newTimes;
               setTimes(newTimes);
               
               if (newTimes === 5) {
                  stopBreathingCycle();
                  return;
               }
            }
            secondsRef.current = 0;
            setPhase(nextPhase);
         }
      }, 1000);

      return () => {
         if (timerRef.current) {
            clearInterval(timerRef.current);
         }
      };
   }, [phase]);

   useEffect(() => {
      startBreathingCycle();
      
      return () => stopBreathingCycle();
   }, []);

   const handleToggle = () => {
      navigate("/");
   };

   return (
      <main className="d-flex flex-column min-vh-100">
         <ProgressBar
            text={text}
            value={value}
         />
         <Container fluid className="d-flex align-items-center justify-content-center flex-grow-1">
            <div className="text-center">
               <h1 className="display-4 mb-4">{title}</h1>
               <Button 
                  onClick={handleToggle}
                  variant="primary"
               >
                 Завершить
               </Button>
            </div>
         </Container>
      </main>
   );
};

export default BreathingPracticePage;