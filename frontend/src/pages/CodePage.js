import { useState } from "react";
import { useNavigate } from 'react-router-dom';
import Button from "../components/ui/Button";
import { PostService } from "../scripts/post-service";
import Input from "../components/ui/Input";
import Container from "../components/layout/Container";

const CodePage = () => {
   const navigate = useNavigate();
   const [code, setCode] = useState("");
   const [errors, setErrors] = useState({});
   const [loading, setLoading] = useState(false);
   const [emailResult, setEmailResult] = useState("");

   const handleInputChange = (name, value, error) => {
      setCode(value);
      setErrors(prev => ({
         ...prev,
         [name]: error
      }));
   };

   const handleInput = async () => {
      setLoading(true);
      try {
         const result = await PostService.postData('http://localhost:8000/auth/verify-code/', {
            code: code
         });
         if (result && result.message === "Успешная авторизация"){
            navigate('/home', { 
               state: { 
                  code: code,
                  user_name: result.user_name,
               } 
            });
         } else {
            setEmailResult(result.message);
         }
      } catch (error) {
         setEmailResult(error.data.detail);
      } finally {
         setLoading(false);
      }
   };

   const handleBack   = () => {
      navigate('/');
   };

   return (
      <main className="d-flex flex-column min-vh-100">
         <Container className="align-items-center justify-content-center">
            <h1>Проверьте свою почту</h1>
            
            <div className="input-group mt-3 justify-content-center">
               <Input
                  type="text"
                  placeholder="Введите код с почты..."
                  name="code"
                  value={code} 
                  onChange={handleInputChange} 
                  required={true}
                  style={{ width: '400px' }} 
               
               />
               <Button 
                  onClick={handleInput}
                  variant="outline-primary"
                  disabled={loading}
                  className="btn-icon"
               >
                  <i className="bi bi-arrow-right-circle-fill"></i>
               </Button>
            </div>
            {emailResult && (
               <div className="mt-3">{emailResult}</div>
            )
            }
            <a onClick={handleBack} className="mt-2">Вернуться</a>
         </Container>
      </main>
      
   );
};

export default CodePage;