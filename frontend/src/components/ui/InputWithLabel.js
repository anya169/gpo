import { useState } from "react";

const InputWithLabel = ({
   label,
   type = "text",
   placeholder = "",
   value = "",
   name,
   required = false,
   onChange,
   error = "",
   disabled = false,
   wrapperClass = "",     
   inputClass = "", 
   ...props
}) => {
   const [internalError, setInternalError] = useState("");
   const validateInput = (required, value, type) => {
      if (required) {
         if (type === 'checkbox'){
            if (!value) {
               return 'Это поле обязательно';
            }
         } else {
            if (!value.toString().trim()) {
               return 'Это поле обязательно';
            }
         }
      }

      if (type === "password"){
         if (value && value.length < 8){
            let passwordError = "Пароль должен содержать не менее 8 символов"
            let newError = error ? error : passwordError
            return newError
         }
      }

      if (value && type === "email"){
         const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
         if (!emailRegex.test(value) || value.length > 254) {
            let emailError = "Введите корректный адрес почты"
            let newError = error ? error : emailError
            return newError
         }
      }

      return "";
   };

   
   const handleInputChange = (event) => {
      const newValue = event.target.value;

      const newError = validateInput(required, newValue, type);
      setInternalError(newError);

      if (onChange) {
         onChange(name, newValue, newError);
      }
   };

   return (
      <div className={wrapperClass}>
      {label && (
         <label className="form-label">{label}</label>
      )}
      <input
         type={type}
         placeholder={placeholder}
         value={value}
         id={name}
         name={name}
         required={required}
         onChange={handleInputChange}
         disabled={disabled}
         className={`form-control ${internalError ? 'is-invalid' : ''} ${inputClass}`}
         {...props}
      />
      {internalError && (
         <div className="invalid-feedback">
            {internalError}
         </div>
      )}
      </div>
   );
};

export default InputWithLabel;