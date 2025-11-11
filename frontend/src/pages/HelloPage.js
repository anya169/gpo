import { useState } from "react";
import Button from "../components/ui/Button";
import InputWithLabel from "../components/ui/InputWithLabel";
import Input from "../components/ui/Input";
import Container from "../components/layout/Container";

const HelloPage = () => {
   const [email, setEmail] = useState("");
   const [errors, setErrors] = useState({});

   const handleInputChange = (name, value, error) => {
      setEmail(value);
      setErrors(prev => ({
         ...prev,
         [name]: error
      }));
   };

   const handleSearch = () => {
      alert(`Поиск для: ${email}`);
   };

   return (
      <main className="d-flex flex-column min-vh-100">
         <Container>
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
                  onClick={handleSearch}
                  variant="outline-primary"
               >
                  <i className="bi bi-arrow-right-circle-fill"></i>
               </Button>
            </div>
         </Container>
      </main>
      
   );
};

export default HelloPage;