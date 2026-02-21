import { focus } from "../Artifact/artifactSlice";
import { useDispatch } from "react-redux";

export default function ArtifactEntry({ artifact }) {
  const dispatch = useDispatch();
  return (
    <div onClick={() => dispatch(focus(artifact.id))}>{artifact.title}</div>
  );
}
