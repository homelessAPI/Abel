import { useState } from 'react'
import './App.css'


const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'


export default function App() {
    const [filters, setFilters] = useState({
        keywords: '',
        location: '',
        experience_level: '',
        employment_type: '',
        remote: '',
        date_posted: 'all',
        source_mode: 'default',
        custom_url: '',
        api_key: '',
        auth_header: 'Authorization'
    })

    const [jobs, setJobs] = useState([])
    const [warnings, setWarnings] = useState([])
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const [searched, setSearched] = useState(false)


    function update_filter(name, value) {
        setFilters(previous_filters => ({
            ...previous_filters,
            [name]: value
        }))
    }


    async function search_jobs(event) {
        event.preventDefault()

        setLoading(true)
        setError('')
        setWarnings([])
        setSearched(true)

        const search_data = {
            keywords: filters.keywords,
            location: filters.location || null,
            experience_level: filters.experience_level || null,
            employment_type: filters.employment_type || null,
            remote: filters.remote === '' ? null : filters.remote === 'true',
            date_posted: filters.date_posted,
            source_mode: filters.source_mode,
            limit: 50
        }

        if (filters.source_mode === 'custom') {
            search_data.custom_source = {
                url: filters.custom_url,
                api_key: filters.api_key || null,
                auth_header: filters.auth_header,
                auth_prefix: filters.auth_header === 'x-api-key' ? '' : 'Bearer '
            }
        }

        try {
            const response = await fetch(API + '/api/jobs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(search_data)
            })

            const response_data = await response.json()

            if (!response.ok) {
                throw new Error(response_data.detail || 'Search failed')
            }

            setJobs(response_data.jobs || [])
            setWarnings(response_data.warnings || [])

        } catch (error) {
            setJobs([])
            setError(error.message)

        } finally {
            setLoading(false)
        }
    }


    return (
        <main className="app-shell">
            <header className="topbar">
                <div className="brand">
                    <span className="brand-mark">A</span> abel
                </div>

                <div className="top-note">
                    One search. Multiple job sources.
                </div>
            </header>


            <section className="hero">
                <div className="eyebrow">
                    Your next opportunity starts here
                </div>

                <h1>
                    Find work that
                    <br />
                    fits your next move.
                </h1>

                <p>
                    Search free remote-job feeds with filters that matter. No paid API key is needed.
                    Or connect your own API when you want more control.
                </p>
            </section>


            <section className="search-panel">
                <div className="panel-heading">
                    <h2>Build your job search</h2>

                    <div className="mode-toggle">
                        <button
                            type="button"
                            className={filters.source_mode === 'default' ? 'active' : ''}
                            onClick={() => update_filter('source_mode', 'default')}
                        >
                            Standard
                        </button>

                        <button
                            type="button"
                            className={filters.source_mode === 'custom' ? 'active' : ''}
                            onClick={() => update_filter('source_mode', 'custom')}
                        >
                            Custom source
                        </button>
                    </div>
                </div>


                <form onSubmit={search_jobs}>
                    <div className="form-grid">
                        <div className="field wide">
                            <label>What kind of role?</label>

                            <input
                                value={filters.keywords}
                                onChange={event => update_filter('keywords', event.target.value)}
                                placeholder="e.g. software engineer, data analyst"
                            />
                        </div>


                        <div className="field wide">
                            <label>Where?</label>

                            <input
                                value={filters.location}
                                onChange={event => update_filter('location', event.target.value)}
                                placeholder="City, state, or remote"
                            />
                        </div>


                        <div className="field">
                            <label>Experience level</label>

                            <select
                                value={filters.experience_level}
                                onChange={event => update_filter('experience_level', event.target.value)}
                            >
                                <option value="">Any experience</option>
                                <option value="entry">Entry level</option>
                                <option value="junior">Junior</option>
                                <option value="mid">Mid-level</option>
                                <option value="senior">Senior</option>
                                <option value="internship">Internship</option>
                            </select>
                        </div>


                        <div className="field">
                            <label>Employment type</label>

                            <select
                                value={filters.employment_type}
                                onChange={event => update_filter('employment_type', event.target.value)}
                            >
                                <option value="">Any type</option>
                                <option value="FULLTIME">Full-time</option>
                                <option value="PARTTIME">Part-time</option>
                                <option value="INTERN">Internship</option>
                                <option value="CONTRACTOR">Contract</option>
                                <option value="TEMPORARY">Temporary</option>
                            </select>
                        </div>


                        <div className="field">
                            <label>Work arrangement</label>

                            <select
                                value={filters.remote}
                                onChange={event => update_filter('remote', event.target.value)}
                            >
                                <option value="">Any arrangement</option>
                                <option value="true">Remote only</option>
                                <option value="false">On-site / hybrid</option>
                            </select>
                        </div>


                        <div className="field">
                            <label>Date posted</label>

                            <select
                                value={filters.date_posted}
                                onChange={event => update_filter('date_posted', event.target.value)}
                            >
                                <option value="all">Any time</option>
                                <option value="today">Today</option>
                                <option value="3days">Last 3 days</option>
                                <option value="week">Last week</option>
                                <option value="month">Last month</option>
                            </select>
                        </div>


                        {filters.source_mode === 'custom' && (
                            <div className="custom-box">
                                <div className="field">
                                    <label>API endpoint (HTTPS)</label>

                                    <input
                                        type="url"
                                        required
                                        value={filters.custom_url}
                                        onChange={event => update_filter('custom_url', event.target.value)}
                                        placeholder="https://api.example.com/jobs"
                                    />
                                </div>


                                <div className="field">
                                    <label>Authentication header</label>

                                    <select
                                        value={filters.auth_header}
                                        onChange={event => update_filter('auth_header', event.target.value)}
                                    >
                                        <option value="Authorization">Authorization: Bearer</option>
                                        <option value="x-api-key">x-api-key</option>
                                    </select>
                                </div>


                                <div className="field">
                                    <label>API key (optional)</label>

                                    <input
                                        type="password"
                                        autoComplete="off"
                                        value={filters.api_key}
                                        onChange={event => update_filter('api_key', event.target.value)}
                                        placeholder="Only sent to Abel backend"
                                    />
                                </div>

                                <p className="custom-help">
                                    Your endpoint should return JSON containing jobs, results, data, or items.
                                    Credentials are used for this search only and are not stored.
                                </p>
                            </div>
                        )}
                    </div>


                    <div className="actions">
                        <button className="search-button" disabled={loading}>
                            {loading ? 'Searching sources...' : 'Find jobs →'}
                        </button>
                    </div>
                </form>
            </section>


            <section aria-live="polite">
                <div className="results-head">
                    <h2>{searched ? 'Search results' : 'Ready when you are'}</h2>

                    <span className="results-meta">
                        {jobs.length} opportunities
                    </span>
                </div>


                {error && (
                    <div className="error-state">
                        {error}
                    </div>
                )}


                {!error && searched && !loading && jobs.length === 0 && (
                    <div className="empty-state">
                        No matching jobs yet. Try broader keywords or check the source warnings.
                    </div>
                )}


                {!searched && (
                    <div className="empty-state">
                        Enter a role or keyword to start exploring opportunities.
                    </div>
                )}


                {warnings.length > 0 && (
                    <ul className="warning-list">
                        {warnings.map((warning, index) => (
                            <li key={index}>{warning}</li>
                        ))}
                    </ul>
                )}


                <div className="job-list">
                    {jobs.map(job => (
                        <article className="job-card" key={job.id || job.url}>
                            <div>
                                <h3 className="job-title">{job.title}</h3>

                                <div className="job-company">
                                    {job.company}
                                </div>

                                <div className="job-details">
                                    <span>{job.location}</span>
                                    <span>{job.employment_type}</span>
                                    <span>{job.remote ? 'Remote' : 'On-site / unspecified'}</span>
                                    <span>{job.salary}</span>
                                    <span className="pill">{job.source}</span>

                                    {job.source_url && (
                                        <a
                                            className="source-link"
                                            href={job.source_url}
                                            target="_blank"
                                            rel="noreferrer"
                                        >
                                            Source ↗
                                        </a>
                                    )}
                                </div>
                            </div>


                            <a
                                className="apply-link"
                                href={job.url}
                                target="_blank"
                                rel="noreferrer"
                            >
                                View opportunity ↗
                            </a>
                        </article>
                    ))}
                </div>
            </section>


            <footer className="footer">
                Abel · Job discovery, without the noise.
            </footer>
        </main>
    )
}
