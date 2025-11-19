import { useState, useEffect, useRef } from "react";
import { useNavigate } from 'react-router-dom';
import Button from "../components/ui/Button";
import ProgressBar from "../components/ui/ProgressBar";
import Container from "../components/layout/Container";

const CalibrationPage = () => {
   const navigate = useNavigate();
   const [text, setText] = useState("1. Нажмите и удерживайте кнопку на корпусе Neiry, лампочка с противоположной стороны начнёт быстро мигать. 2. Найдите в списках устройств Bluetooth «Headband» и подключите его");
   const [title, setTitle] = useState("Подключите нейроинтерфейс");
   const [step, setstep] = useState("calibrate");
   const [className, setClassName] = useState("");
   const [classText, setClassText] = useState(""); 
   const timeoutRef = useRef(null);

   const steps = {
      put_on: { next: "calibrate", title: "Наденьте нейроинтерфейс", text: "Убедитесь, что датчики плотно прилегают к голове" },
      calibrate: { next: "close", title: "Начните калибровку", text: "При калибровке вам нужно будет закрыть глаза. Вы услышите звуковой сигнал, когда калибровка закончится" },
      close: { next: "final", title: "Закройте глаза, идёт калибровка", text: "Вы услышите звуковой сигнал по окончании" },
      final: { next: "", title: "Калибровка завершена", text: "Теперь вы можете начать сессию"}
   };

   const handleToggle = () => {
      const currentstep = steps[step];
      setText(currentstep.text);
      setTitle(currentstep.title);
      if (step === "close") {
         setClassName("bg-black");
         setClassText("text-white");
         timeoutRef.current = setTimeout(() => {
            const audio = new Audio('/sounds/calibration-complete.mp3');
            audio.play().catch(error => {
               console.log("Ошибка воспроизведения звука:", error);
            });
         }, 10000);
      } else {
         setClassName("bg-white");
         setClassText("text-black");
      }
      setstep(currentstep.next); 
   };

   return (
      <main className={`d-flex flex-column min-vh-100 ${className}`}>
         <Container fluid className="d-flex align-items-center justify-content-center flex-grow-1 w-75">
            <div className={`text-center ${classText}`}>
               <h1 className="display-4 mb-4">{title}</h1>
               <div className="display-6 mb-5">{text}</div>
               <Button 
                  onClick={handleToggle}
                  variant="primary"
               >
                 Далее
               </Button>
            </div>
         </Container>
      </main>
   );
};

export default CalibrationPage;