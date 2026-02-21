import { useDispatch } from "react-redux";
import EditableText from "../components/EditableText";
import { refresh } from "./artifactSlice";

export default function Fact({ factId }) {
  const dispatch = useDispatch();
  const unescape = (entry) => {
    if (!entry) return "";
    return entry.replaceAll("\\n", "\n");
  };
  return (
    <EditableText
      get={() =>
        fetch(`/api/fact/${factId}`)
          .then((res) => res.json())
          .then((data) => unescape(data[0].entry))
      }
      set={(value) =>
        fetch(`/api/fact/${factId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            // 'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: JSON.stringify({
            entry: value,
          }),
        })
      }
      del={() =>
        fetch(`/api/fact/${factId}`, { method: "DELETE" }).then(() =>
          dispatch(refresh(true))
        )
      }
    />
  );
}
