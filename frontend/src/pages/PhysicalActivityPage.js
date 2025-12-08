import { useState, useEffect, useRef } from "react";
import { useNavigate } from 'react-router-dom';
import Button from "../components/ui/Button";
import ProgressBar from "../components/ui/ProgressBar";
import Container from "../components/layout/Container";

const PhysicalActivityPage = () => {
   const navigate = useNavigate();
   const [text, setText] = useState("Ровное дыхание и повторяющиеся движения помогают мозгу войти в сосредоточенное состояние");
   const [title, setTitle] = useState("Легкий бег на месте или ходьба");
   const [step, setstep] = useState("activity");
   const [gif, setGif] = useState("run");
   const [width, setWidth] = useState("200px");
   const [button, setButton] = useState("Далее");

   const steps = {
      activity: { gif: "activity", next: "dance", title: "Выполните упражнение", text: "Отжимания, приседания, повороты головы способствуют улучшению кровообращения" },
      dance: { gif: "dance", next: "", title: "Включите любимую музыку и потанцуйте!", text: "Любимые песни повышают уровень дофамина" },
   };

   const handleToggle = () => {
      if (button === "Завершить"){
         navigate("/session");
      }
      const currentstep = steps[step];
      setText(currentstep.text);
      setTitle(currentstep.title);
      setGif(currentstep.gif);
      if (step === "dance") {
         setButton(`Завершить`);
         setWidth("350px");
      } else {
         setWidth("500px");
      }
      setstep(currentstep.next); 
   };

   return (
      <main className={`d-flex flex-column min-vh-100`}>
         <Container fluid className="d-flex align-items-center justify-content-center flex-grow-1 w-75">
            <div className={`text-center`}>
               <h1 className="display-4 mb-4">{title}</h1>
               <div className="display-6 mb-5">{text}</div>
               <img 
                  src={`/gifs/${gif}.gif`}
                  style={{ 
                     width: width, 
                     height: 'auto',
                  }}
               /> 
            </div>
            <Button 
               className="mt-5"
               onClick={handleToggle}
               variant="primary"
            >
               {button}
            </Button>
         </Container>
      </main>
   );
};

export default PhysicalActivityPage;