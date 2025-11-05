const Input = ({
   label,
   type = "text",
   placeholder = "",
   value,
   onChange,
   error = "",
   disabled = false,
   className = ""
}) => {
   return (
      <div className="mb-3">
      {label && (
         <label className="form-label">{label}</label>
      )}
      <input
         type={type}
         placeholder={placeholder}
         value={value}
         onChange={onChange}
         disabled={disabled}
         className={`form-control ${error ? 'is-invalid' : ''} ${className}`}
      />
      {error && (
         <div className="invalid-feedback">
            {error}
         </div>
      )}
      </div>
   );
};

export default Input;