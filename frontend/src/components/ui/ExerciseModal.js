import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const ExerciseModal = ({ show, onClose, exerciseData }) => {
const navigate = useNavigate();
const [isVisible, setIsVisible] = useState(show);

useEffect(() => {
   setIsVisible(show);
}, [show]);

if (!isVisible) return null;

const handleExerciseClick = (type) => {
   onClose();
   
   if (type === 'breathing') {
      navigate('/breathing-exercise');
   } else if (type === 'movement') {
      navigate('/movement-exercise');
   }
};

const handleClose = () => {
   setIsVisible(false);
   setTimeout(() => {
      onClose();
   }, 300);
};

return (
   <div className="modal show d-block" tabIndex="-1" style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}>
      <div className="modal-dialog modal-dialog-centered">
      <div className="modal-content">
         <div className="modal-header bg-warning">
            <h5 className="modal-title">
            ⚠️ Рекомендуем сделать перерыв
            </h5>
            <button 
            type="button" 
            className="btn-close" 
            onClick={handleClose}
            ></button>
         </div>
         
         <div className="modal-body">
            <div className="text-center mb-4">
            <p className="mb-1">
               Уровень концентрации снизился: <strong>{exerciseData?.current_concentration?.toFixed(1)}</strong>
            </p>
            <p className="text-muted small">
               Рекомендуем сделать короткое упражнение для восстановления фокуса
            </p>
            </div>

            <div className="row g-3">
            <div className="col-md-6">
               <div 
                  className="card h-100 text-center border-primary hover-shadow"
                  style={{ cursor: 'pointer' }}
                  onClick={() => handleExerciseClick('breathing')}
               >
                  <div className="card-body">
           
                  <h5 className="card-title text-primary">Дыхательное упражнение</h5>
                  <p className="card-text text-muted small">
                     Упражнение на глубокое дыхание для снятия стресса и улучшения концентрации
                  </p>
                 
                  </div>
               </div>
            </div>

            <div className="col-md-6">
               <div 
                  className="card h-100 text-center border-success hover-shadow"
                  style={{ cursor: 'pointer' }}
                  onClick={() => handleExerciseClick('movement')}
               >
                  <div className="card-body">
                 
                  <h5 className="card-title text-success">Двигательное упражнение</h5>
                  <p className="card-text text-muted small">
                     Легкие физические упражнения для снятия напряжения и повышения энергии
                  </p>
                 
                  </div>
               </div>
            </div>
            </div>

            <div className="mt-4 text-center">
            <p className="text-muted small mb-2">
               После упражнения концентрация может повыситься на 15-25%
            </p>
            </div>
         </div>

         <div className="modal-footer">
            <button 
            type="button" 
            className="btn btn-outline-secondary"
            onClick={handleClose}
            >
            Пропустить
            </button>
         </div>
      </div>
      </div>
   </div>
);
};

export default ExerciseModal;