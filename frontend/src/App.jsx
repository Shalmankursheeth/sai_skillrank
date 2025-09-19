import { BrowserRouter as Router } from "react-router-dom";
import Nav from "./components/Nav";

export default function App(){
  return (
    <Router>
      <div style={{minHeight: "100vh", background: "#F9FAFB"}}>
        <Nav />
        <main className="container mx-auto p-4">
          <h2 className="text-lg font-semibold mt-4">Router + Nav restored — pages not mounted</h2>
        </main>
      </div>
    </Router>
  );
}
