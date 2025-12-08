import { useState, useEffect, useRef } from 'react';
import { Line } from 'react-chartjs-2';
import { useNavigate } from 'react-router-dom';
import {
Chart as ChartJS,
CategoryScale,
LinearScale,
PointElement,
LineElement,
Title,
Tooltip,
Legend
} from 'chart.js';
import ExerciseModal from './ExerciseModal'; // Импортируйте компонент

ChartJS.register(
CategoryScale,
LinearScale,
PointElement,
LineElement,
Title,
Tooltip,
Legend
);

const ConcentrationChart = () => {
const [chartData, setChartData] = useState({
   labels: [],
   datasets: [
      {
      label: 'Концентрация',
      data: [],
      borderColor: 'rgba(75, 192, 192, 1)',
      backgroundColor: 'rgba(75, 192, 192, 0.1)',
      tension: 0.4,
      fill: true,
      pointBackgroundColor: 'rgb(75, 192, 192)',
      pointBorderColor: 'white',
      pointBorderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
      }
   ]
});

const [currentData, setCurrentData] = useState({
   concentration: 0,
   stress: 0,
   heart_rate: 0,
   focus: 0,
   timestamp: '',
   data_index: 0,
   total_points: 0
});

const [isStreaming, setIsStreaming] = useState(false);
const [connectionStatus, setConnectionStatus] = useState('disconnected');
const [isLoading, setIsLoading] = useState(false);
const [hasSentStartCommand, setHasSentStartCommand] = useState(false);
const [showExerciseModal, setShowExerciseModal] = useState(false);
const [exerciseData, setExerciseData] = useState(null);
const ws = useRef(null);
const navigate = useNavigate();

useEffect(() => {
   connectWebSocket();
   return () => {
      if (ws.current) {
      ws.current.close();
      }
   };
}, []);

const connectWebSocket = () => {
   try {
      ws.current = new WebSocket('ws://localhost:8000/ws/neiry/file-stream');
      
      ws.current.onopen = () => {
         setConnectionStatus('connected');
         setIsLoading(false);
         setHasSentStartCommand(false);
         
         if (isStreaming && !hasSentStartCommand) {
            setTimeout(() => {
               startFileStream();
            }, 1000);
         }
      };

      ws.current.onmessage = (event) => {
         try {
            const message = JSON.parse(event.data);
            handleWebSocketMessage(message);
         } catch (error) {
            console.error('Ошибка парсинга:', error);
         }
      };

      ws.current.onclose = (event) => {
         setConnectionStatus('disconnected');
         
         if (event.code !== 1000 && isStreaming) {
            setTimeout(connectWebSocket, 3000);
         }
      };

      ws.current.onerror = (error) => {
         setConnectionStatus('error');
         setIsLoading(false);
      };
   } catch (error) {
      setIsLoading(false);
   }
};

const handleWebSocketMessage = (message) => {
   switch (message.type) {
      case 'connection_established':
         setConnectionStatus('connected');
         break;
      
      case 'concentration_data':
         if (message.data && typeof message.data.concentration !== 'undefined') {
            updateChartData(message.data);
            
            if (message.data.concentration < 30) { 
               showExerciseSuggestion(message.data);
            }
         }
         break;
      
      case 'stream_started':
         setIsStreaming(true);
         setIsLoading(false);
         setHasSentStartCommand(true);
         break;
      
      case 'stream_stopped':
         setIsStreaming(false);
         setHasSentStartCommand(false);
         break;
      
      case 'error':
         setIsLoading(false);
         setIsStreaming(false);
         setHasSentStartCommand(false);
         break;
      
      case 'exercise_suggestion':
      case 'exercise_notification':
         if (message.exercises || message.current_concentration) {
            showExerciseSuggestion(message);
         }
         break;
      
      default:
         if (message && typeof message.concentration !== 'undefined') {
            updateChartData(message);
         }
   }
};

const showExerciseSuggestion = (data) => {
   setExerciseData({
      current_concentration: data.concentration || data.current_concentration,
      timestamp: new Date().toLocaleTimeString(),
      exercises: data.exercises || [
         { id: 1, name: 'Дыхательное упражнение', type: 'breathing', duration: 5 },
         { id: 2, name: 'Двигательное упражнение', type: 'movement', duration: 3 }
      ]
   });
   
   setTimeout(() => {
      setShowExerciseModal(true);
   }, 1000);
};

const updateChartData = (data) => {
   if (!data || typeof data.concentration === 'undefined') {
      return;
   }
   
   const concentration = parseFloat(data.concentration) || 0;
   const stress = parseFloat(data.stress) || 0;
   const heart_rate = parseFloat(data.heart_rate) || 0;
   const focus = parseFloat(data.focus) || 0;
   const timestamp = data.timestamp || new Date().toLocaleTimeString();
   const data_index = data.data_index || 0;
   const total_points = data.total_points || 0;

   setCurrentData({
      concentration,
      stress,
      heart_rate,
      focus,
      timestamp,
      data_index,
      total_points
   });

   setChartData(prev => {
      const newLabels = [...prev.labels, timestamp];
      const newData = [...prev.datasets[0].data, concentration];
      
      const limitedLabels = newLabels.slice(-50);
      const limitedData = newData.slice(-50);
      
      return {
         labels: limitedLabels,
         datasets: [
            {
               ...prev.datasets[0],
               data: limitedData
            }
         ]
      };
   });
};

const startFileStream = () => {
   if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      if (hasSentStartCommand) {
         return;
      }
      
      setIsLoading(true);
      setHasSentStartCommand(true);
      
      ws.current.send(JSON.stringify({
         type: 'start_stream',
         session_id: 1,
         speed: 1.0
      }));
      
      setTimeout(() => {
         if (isLoading && !isStreaming) {
            setIsLoading(false);
            setHasSentStartCommand(false);
         }
      }, 5000);
      
   } else {
      setHasSentStartCommand(false);
   }
};

const stopFileStream = () => {
   if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
         type: 'stop_stream'
      }));
   }
};

const setStreamSpeed = (speed) => {
   if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
         type: 'set_speed',
         speed: speed
      }));
   }
};

const clearChart = () => {
   setChartData({
      labels: [],
      datasets: [
         {
            ...chartData.datasets[0],
            data: []
         }
      ]
   });
   setCurrentData({
      concentration: 0,
      stress: 0,
      heart_rate: 0,
      focus: 0,
      timestamp: '',
      data_index: 0,
      total_points: 0
   });
};

const handleExerciseSelect = (exerciseType) => {
   setShowExerciseModal(false);
   
   // Отправляем на сервер информацию о выбранном упражнении
   if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
         type: 'exercise_selected',
         exercise_type: exerciseType,
         session_id: 1
      }));
   }
   
   // Переход на страницу упражнения
   if (exerciseType === 'breathing') {
      navigate('/breathing-exercise');
   } else if (exerciseType === 'movement') {
      navigate('/movement-exercise');
   }
};

const chartOptions = {
   responsive: true,
   maintainAspectRatio: false,
   plugins: {
      legend: {
         display: true,
         position: 'top',
         labels: {
            font: {
               size: 14
            }
         }
      },
      title: {
         display: true,
         text: 'Уровень концентрации',
         font: {
            size: 18,
            weight: 'bold'
         },
         padding: {
            top: 10,
            bottom: 30
         }
      },
      tooltip: {
         mode: 'index',
         intersect: false,
         backgroundColor: 'rgba(0, 0, 0, 0.7)',
         titleFont: {
            size: 14
         },
         bodyFont: {
            size: 13
         },
         callbacks: {
            label: function(context) {
               return `Концентрация: ${context.parsed.y.toFixed(1)}%`;
            }
         }
      }
   },
   scales: {
      y: {
         beginAtZero: true,
         min: 0,
         max: 100,
         title: {
            display: true,
            text: 'Уровень концентрации (%)',
            font: {
               size: 14,
               weight: 'bold'
            }
         },
         grid: {
            color: 'rgba(0, 0, 0, 0.1)'
         },
         ticks: {
            font: {
               size: 12
            }
         }
      },
      x: {
         title: {
            display: true,
            text: 'Время',
            font: {
               size: 14,
               weight: 'bold'
            }
         },
         grid: {
            color: 'rgba(0, 0, 0, 0.05)'
         },
         ticks: {
            font: {
               size: 12
            },
            maxTicksLimit: 10
         }
      }
   },
   interaction: {
      intersect: false,
      mode: 'nearest'
   },
   animation: {
      duration: 0
   },
   elements: {
      line: {
         borderWidth: 2
      }
   }
};

useEffect(() => {
   const initialData = {
      concentration: 0,
      stress: 0,
      heart_rate: 0,
      focus: 0,
      timestamp: 'Загрузка...',
      data_index: 0,
      total_points: 0
   };
   
   setCurrentData(initialData);
   setChartData({
      labels: ['Начало'],
      datasets: [
         {
            label: 'Концентрация',
            data: [initialData.concentration],
            borderColor: 'rgba(75, 192, 192, 1)',
            backgroundColor: 'rgba(75, 192, 192, 0.1)',
            tension: 0.4,
            fill: true,
            pointBackgroundColor: 'rgb(75, 192, 192)',
            pointBorderColor: 'white',
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
         }
      ]
   });
}, []);

return (
   <>
      <div className="container mt-4">
         <div className="row">
            <div className="col-12">
               <div className="card shadow-sm">
                  <div className="card-header bg-white">
                     <div className="d-flex justify-content-between align-items-center">
                        <h5 className="mb-0 text-primary">
                           Мониторинг концентрации
                        </h5>
                        <div className="d-flex align-items-center gap-2">
                           <div className={`badge ${connectionStatus === 'connected' ? 'bg-success' : 
                              connectionStatus === 'error' ? 'bg-danger' : 'bg-warning'}`}>
                              {connectionStatus === 'connected' ? 'Подключено' : 
                              connectionStatus === 'error' ? 'Ошибка' : 'Отключено'}
                           </div>
                           <div className={`badge ${isStreaming ? 'bg-success' : 'bg-secondary'}`}>
                              {isStreaming ? 'Идет запись' : 'Пауза'}
                           </div>
                           {isLoading && (
                              <div className="badge bg-info">
                                 <span className="spinner-border spinner-border-sm me-1"></span>
                                 Запуск...
                              </div>
                           )}
                        </div>
                     </div>
                  </div>

                  <div className="card-body">
                     <div className="row mb-4">
                        <div className="col-md-4 col-6 mb-3">
                           <div className="card border-primary shadow-sm">
                              <div className="card-body text-center py-3">
                                 <h6 className="card-title text-muted mb-2">
                                    Концентрация
                                 </h6>
                                 <h2 className="text-primary mb-0">
                                    {currentData.concentration?.toFixed(1)}
                                 </h2>
                              </div>
                           </div>
                        </div>
                        
                        <div className="col-md-4 col-6 mb-3">
                           <div className="card border-warning shadow-sm">
                              <div className="card-body text-center py-3">
                                 <h6 className="card-title text-muted mb-2">
                                    Стресс
                                 </h6>
                                 <h2 className="text-warning mb-0">
                                    {currentData.stress?.toFixed(1)}
                                 </h2>
                              </div>
                           </div>
                        </div>
                        
                        <div className="col-md-4 col-6 mb-3">
                           <div className="card border-info shadow-sm">
                              <div className="card-body text-center py-3">
                                 <h6 className="card-title text-muted mb-2">
                                    Фокус
                                 </h6>
                                 <h2 className="text-info mb-0">
                                    {currentData.focus?.toFixed(1)}
                                 </h2>
                              </div>
                           </div>
                        </div>
                     </div>

                     <div className="mb-4" style={{ height: '400px', position: 'relative' }}>
                        <Line data={chartData} options={chartOptions} />
                     </div>

                     <div className="row mb-3">
                        <div className="col-12">
                           <div className="d-flex flex-wrap gap-2 justify-content-center align-items-center">
                           <button 
                              className={`btn ${isStreaming ? 'btn-danger' : 'btn-success'} px-4`}
                              onClick={isStreaming ? stopFileStream : startFileStream}
                              disabled={connectionStatus !== 'connected' || isLoading}
                           >
                              {isLoading ? (
                                 <>
                                    <span className="spinner-border spinner-border-sm me-2" role="status"></span>
                                    Запуск...
                                 </>
                              ) : isStreaming ? (
                                 <>
                                    <span className="me-2">■</span>
                                    Стоп
                                 </>
                              ) : (
                                 <>
                                    <span className="me-2">▶</span>
                                    Старт
                                 </>
                              )}
                           </button>
                           
                           <button 
                              className="btn btn-secondary px-4"
                              onClick={clearChart}
                              disabled={chartData.datasets[0].data.length === 0}
                           >
                              <span className="me-2">×</span>
                              Очистить
                           </button>
                           
                           <div className="input-group" style={{ width: '220px' }}>
                              <span className="input-group-text bg-light">
                                 Скорость
                              </span>
                              <select 
                                 className="form-select"
                                 onChange={(e) => setStreamSpeed(parseFloat(e.target.value))}
                                 defaultValue="1.0"
                                 disabled={!isStreaming}
                              >
                                 <option value="0.5">0.5x</option>
                                 <option value="1.0">1.0x</option>
                                 <option value="2.0">2.0x</option>
                                 <option value="5.0">5.0x</option>
                              </select>
                           </div>
                           </div>
                        </div>
                     </div>
                  </div>
               </div>
            </div>
         </div>
      </div>

      <ExerciseModal 
         show={showExerciseModal}
         onClose={() => setShowExerciseModal(false)}
         exerciseData={exerciseData}
      />
   </>
);
};

export default ConcentrationChart;