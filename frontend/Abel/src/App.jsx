import { useState } from 'react'
import './App.css'

function App() {
  const [search_query, setSearchQuery] = useState('')
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState('')
  const [error, setError] = useState('')

  async function handle_submit(e){
    e.preventDefault()

    setLoading(true)
    try {

      const search = {
        search: search_query
      }

      const response = await fetch("http://127.0.0.1:1011/",
        {
        method: 'POST', 
        headers: {'content-type': "application/json"
        },
        body: JSON.stringify(search)
        })

        console.log("response: ", response)

        const data = await response.json()
        console.log(data)

        if (!response.ok) {
          setJobs([])
          setError( data.detail || "an error has occured")
        }
        else {
          setJobs(data.jobs)
          setError(null)
        }
      }
    catch (error) {
      setJobs([])
      setError("an error has occured")
    }
    finally{
      setLoading(false)
    }

  }

  return (
    <>
    <div className='Search-Criteria'>
      <fieldset>
        <legend>Jobs</legend>

        <input type="text" placeholder='Search' value={search_query} onChange={(e)=>setSearchQuery(e.target.value)}/>
        <button onClick={handle_submit} disabled={loading}>{loading? 'Searching...' : 'Search'}</button>

        {loading ? <p> searching ...</p>: null}
        <table>
          <thead>
            <tr>
              <th>Ttle</th>
              <th>Company</th>
              <th>Location</th>
              <th>Is Remote?</th>
              <th>Apply</th>
            </tr>
          </thead>
          <tbody>
            {jobs.length > 0?
              jobs.map((job, index) =>
              <tr key={index}>
                <td>{job.Job_Title}</td>
                <td>{job.Company_Name}</td>
                <td>{job.Location}</td>
                <td>{job.is_remote}</td>
                <td><a href='{job.URL}'>Apply Link</a></td>
              </tr>): <tr>
                <td colSpan='3'>No jobs found...</td>
              </tr>
            }
          </tbody>
        </table>
      </fieldset>
    </div>
    </>
  )
}
export default App
