import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Home from './pages/Home'
import Challenges from './pages/Challenges'
import Showcase from './pages/Showcase'
import Explore from './pages/Explore'
import NewProject from './pages/NewProject'
import ProjectPage from './pages/ProjectPage'
import Profile from './pages/Profile'
import MentorInbox from './pages/MentorInbox'
import Messages from './pages/Messages'
import Admin from './pages/Admin'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/register" element={<Landing register />} />
      <Route element={<Layout />}>
        <Route path="/feed" element={<Home />} />
        <Route path="/explore" element={<Explore />} />
        <Route path="/showcase" element={<Showcase />} />
        <Route path="/challenges" element={<Challenges />} />
        <Route path="/projects/new" element={<NewProject />} />
        <Route path="/projects/:id" element={<ProjectPage />} />
        <Route path="/u/:id" element={<Profile />} />
        <Route path="/mentor" element={<MentorInbox />} />
        <Route path="/messages" element={<Messages />} />
        <Route path="/admin" element={<Admin />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
