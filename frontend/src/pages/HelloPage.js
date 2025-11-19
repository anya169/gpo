import { useState } from "react";
import { useNavigate } from 'react-router-dom';
import Button from "../components/ui/Button";
import { PostService } from "../scripts/post-service";
import Input from "../components/ui/Input";
import Container from "../components/layout/Container";

const HelloPage = () => {
   const navigate = useNavigate();
   const [email, setEmail] = useState("");
   const [errors, setErrors] = useState({});
   const [loading, setLoading] = useState(false);
   const [emailResult, setEmailResult] = useState("");

   const handleInputChange = (name, value, error) => {
      setEmailResult("");
      setEmail(value);
      setErrors(prev => ({
         ...prev,
         [name]: error
      }));
   };

   const handleInput = async () => {
      if (email === ""){
         setEmailResult("Поле обязательно для заполнения");
         return;
      }
      if (errors.email) {
         return;
      }
      setLoading(true);
      setEmailResult("");
      try {
         const result = await PostService.postData('http://localhost:8000/auth/send-code/', {
            email: email
         });
         if (result && result.message){
            navigate('/send-code', { 
               state: { 
                  email: email,
                  user_name: result.user_name,
               } 
            });
         }
      } catch (error) {
         setEmailResult(error.data.detail);
      } finally {
         setLoading(false);
      }
   };

   const handleRegistration = () => {
      navigate('/registration');
   };

   return (
      <main className="d-flex flex-column min-vh-100 ">
         <Container className="align-items-center justify-content-center">
            <h1>Добро пожаловать в Concentration Meter</h1>
            
            <div className="input-group mt-3 justify-content-center">
               <Input
                  type="email"
                  placeholder="Введите адрес электронной почты..."
                  name="email"
                  value={email} 
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
            <a onClick={handleRegistration} className="mt-2">Регистрация</a>
         </Container>
      </main>
      
   );
};

export default HelloPage;