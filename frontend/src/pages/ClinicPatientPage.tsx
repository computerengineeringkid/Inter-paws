import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../utils/api";
import { Pet, User } from "../types";

interface PatientListResponse {
  pets: Pet[];
  owners: User[];
}

export function ClinicPatientPage() {
  const {
    data: patientData,
    isLoading,
    isError,
  } = useQuery<PatientListResponse>({
    queryKey: ["clinicPatients"],
    queryFn: () => apiFetch("/api/clinic/patients"),
  });

  if (isLoading) return <div>Loading patient data...</div>;
  if (isError) return <div>Error loading patient data.</div>;

  const { pets = [], owners = [] } = patientData || {};
  const ownerMap = new Map(owners.map((owner) => [owner.id, owner.full_name]));

  return (
    <main className="content">
      <div className="card">
        <h2>Patient Management</h2>
        <p>View all pets and owners registered with your clinic.</p>
      </div>

      <div className="card-container">
        <div className="card">
          <h3>Pets</h3>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Species</th>
                <th>Breed</th>
                <th>Owner</th>
              </tr>
            </thead>
            <tbody>
              {pets.map((pet) => (
                <tr key={pet.id}>
                  <td>{pet.name}</td>
                  <td>{pet.species}</td>
                  <td>{pet.breed}</td>
                  <td>{ownerMap.get(pet.user_id) || "N/A"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <h3>Owners (Clients)</h3>
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
              </tr>
            </thead>
            <tbody>
              {owners.map((owner) => (
                <tr key={owner.id}>
                  <td>{owner.full_name}</td>
                  <td>{owner.email}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}