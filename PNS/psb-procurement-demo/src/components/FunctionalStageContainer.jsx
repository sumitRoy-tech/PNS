import React, { useEffect, useState } from "react";
import FunctionalAnalysis from "./FunctionalAnalysis";
import FunctionalStageContainer from "./FunctionalStageContainer";


function FunctionalStageContainer({ onComplete }) {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [loading, setLoading] = useState(true);

  // 1️⃣ Load all projects
  useEffect(() => {
    fetch("http://localhost:8003/functional/get-projects")
      .then(res => res.json())
      .then(data => {
        // Prefer projects WITHOUT assessment
        const pending = data.projects.find(p => !p.has_assessment) || data.projects[0];
        setProjects(data.projects);
        if (pending) {
          loadProjectDetails(pending.project_id);
        }
      })
      .catch(err => {
        console.error("Failed to load projects", err);
        alert("Failed to load projects from server");
      });
  }, []);

  // 2️⃣ Load single project details
  const loadProjectDetails = async (projectId) => {
    try {
      setLoading(true);
      const res = await fetch(`http://localhost:8003/functional/projects/${projectId}`);
      const data = await res.json();

      if (!res.ok) {
        alert("Failed to load project details");
        return;
      }

      // Convert backend format → frontend format (keep UI unchanged)
      const req = {
        project_id: data.project.project_id,
        reqId: data.project.project_id,
        title: data.project.title,
        department: data.project.department,
        estimatedValue: data.project.estimated_amount + " Cr", // just for display
      };

      setSelectedProject(req);
    } catch (err) {
      console.error(err);
      alert("Error loading project details");
    } finally {
      setLoading(false);
    }
  };

  if (loading || !selectedProject) {
    return (
      <div className="text-white p-6">
        Loading project for functional analysis...
      </div>
    );
  }

  return (
    <FunctionalAnalysis
      requirement={selectedProject}
      onComplete={onComplete}
    />
  );
}

export default FunctionalStageContainer;
