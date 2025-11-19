import { useState } from "react";
import { useNavigate } from 'react-router-dom';
import Button from "../components/ui/Button";
import { PostService } from "../scripts/post-service";
import InputWithLabel from "../components/ui/InputWithLabel";
import Container from "../components/layout/Container";

const RegistrationPage = () => {
   const navigate = useNavigate();
   const [email, setEmail] = useState("");
   const [name, setName] = useState("");
   const [errors, setErrors] = useState({});
   const [loading, setLoading] = useState(false);
   const [emailResult, setEmailResult] = useState("");

   const handleInputChange = (name, value, error) => {
      if (name === "email"){
         setEmail(value);
      } else {
         setName(value);
      }
      setErrors(prev => ({
         ...prev,
         [name]: error
      }));
   };

   const handleInput = async () => {
      setLoading(true);
      try {
         const result = await PostService.postData('http://localhost:8000/auth/register/', {
            email: email,
            name: name
         }, 'form');
         if (result && result.message){
            navigate('/home', { 
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

   const handleAuth = () => {
      navigate('/');
   };

   return (
      <main className="d-flex flex-column min-vh-100">
         <Container className="align-items-center justify-content-center">
            <h1>Регистрация</h1>
            
            <InputWithLabel
               label="Имя"
               type="text"
               placeholder="Введите свое имя..."
               name="name"
               value={name} 
               onChange={handleInputChange} 
               required={true}
               style={{ width: '400px' }} 
               wrapperClass="mt-2"
            />
            <InputWithLabel
               label="Email"
               type="email"
               placeholder="Введите адрес электронной почты.."
               name="email"
               value={email} 
               onChange={handleInputChange} 
               required={true}
               style={{ width: '400px' }} 
               wrapperClass="mt-2"
            />
            <Button 
               onClick={handleInput}
               variant="outline-primary"
               disabled={loading}
               className="mt-3"
            >
               Зарегистрироваться
            </Button>
            {emailResult && (
               <div className="mt-3">{emailResult}</div>
            )
            }
            <a onClick={handleAuth} className="mt-2">Вернуться к авторизации</a>
         </Container>
      </main>
      
   );
};

export default RegistrationPage;