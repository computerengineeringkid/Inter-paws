import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../utils/api";
import { useAuth } from "../context/AuthContext";

interface PetPayload {
  id: number;
  name: string;
  species: string;
  breed: string | null;
  owner_name: string | null;
}

interface OwnerPayload {
  id: number;
  name: string | null;
  email: string;
}

interface PatientListResponse {
  pets: PetPayload[];
  owners: OwnerPayload[];
}

function ClinicPatientPage() {
  const { token, logout } = useAuth();
  const patientsQuery = useQuery({
    queryKey: ["clinic-patients"],
    queryFn: async () => {
      const response = await apiFetch<PatientListResponse>("/clinic/patients", {
        method: "GET",
        token,
      });
      return response;
    },
  });

  return (
    <>
    <div className="card">
      <h1>Patient Management</h1>
      <p style={{ color: "#4b5563" }}>
        View all pets and their owners registered with your clinic.
      </p>
    </div>
    <div className="card">
      <h2>Pets</h2>
      {patientsQuery.isLoading ? <p>Loading pets...</p> : null}
      {patientsQuery.isError ? <p>Error loading pets.</p> : null}
      {patientsQuery.data?.pets?.length ? (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Species</th>
              <th>Breed</th>
              <th>Owner</th>
            </tr>
          </thead>
          <tbody>
            {patientsQuery.data.pets.map((pet) => (
              <tr key={pet.id}>
                <td>{pet.name}</td>
                <td>{pet.species}</td>
                <td>{pet.breed ?? "—"}</td>
                <td>{pet.owner_name ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>No pets registered yet.</p>
      )}
    </div>
    <div className="card">
      <h2>Owners</h2>
      {patientsQuery.isLoading ? <p>Loading owners...</p> : null}
      {patientsQuery.isError ? <p>Error loading owners.</p> : null}
      {patientsQuery.data?.owners?.length ? (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
            </tr>
          </thead>
          <tbody>
            {patientsQuery.data.owners.map((owner) => (
              <tr key={owner.id}>
                <td>{owner.name ?? "—"}</td>
                <td>{owner.email}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p>No owners registered yet.</p>
      )}
    </div>
    </>
  );
}

export default ClinicPatientPage;