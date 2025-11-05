const Button = ({ 
   children, 
   variant = "primary", 
   size = "md",
   disabled = false,
   onClick,
   type = "button",
   className = ""
}) => {
   const sizeClass = {
      sm: "btn-sm",
      md: "",
      lg: "btn-lg"
   };

  return (
   <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`btn btn-${variant} ${sizeClass[size]} ${className}`}
   >
      {children}
   </button>
  );
};

export default Button;